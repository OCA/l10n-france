# Copyright 2024 Akretion (http://www.akretion.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import binascii
import hmac
import logging
import urllib.parse
import hashlib
from base64 import b64decode
from datetime import datetime, timezone

import pytz
import rsa
from werkzeug import urls

from odoo import api, fields, models
from odoo.modules.module import get_resource_path
from odoo.tools.translate import _

from odoo.addons.payment.models.payment_acquirer import ValidationError

from ..controllers.main import PayBoxController
from .const import PAYBOX_ISO_CURRENCIES

_logger = logging.getLogger(__name__)

IN_DATE_FORMAT = "%d%m%Y_a_%H:%M:%S"
PATH_PUBKEY_MODULE = get_resource_path("payment_paybox", "data/pubkey.pem")
if PATH_PUBKEY_MODULE is False:
    PATH_PUBKEY_MODULE = "False"


class AcquirerPaybox(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(
        selection_add=[("paybox", "Paybox")],
        ondelete={"paybox": "set default"},
    )
    paybox_ept = fields.Char(
        "EPT number PBX_SITE", required_if_provider="paybox", groups="base.group_user"
    )
    paybox_company_code = fields.Char(
        "Company code PBX_IDENTIFIANT",
        required_if_provider="paybox",
    )
    paybox_rang = fields.Char(
        "PBX_rang",
        required_if_provider="paybox",
    )
    paybox_secret = fields.Char(
        "Secret Key", required_if_provider="paybox", groups="base.group_user"
    )
    paybox_test_url = fields.Char(
        "Test url",
        required_if_provider="paybox",
        default="https://preprod-tpeweb.paybox.com/cgi/MYchoix_pagepaiement.cgi",
    )
    paybox_prod_url = fields.Char(
        "Production url",
        required_if_provider="paybox",
        default="https://tpeweb.paybox.com/cgi/MYchoix_pagepaiement.cgi",
    )
    paybox_prod_url_2 = fields.Char(
        "Production url",
        required_if_provider="paybox",
        default="https://tpeweb1.paybox.com/cgi/MYchoix_pagepaiement.cgi",
    )
    paybox_public_key = fields.Char(
        "Public key paybox",
        required_if_provider="paybox",
        default=PATH_PUBKEY_MODULE,
    )

    def _paybox_generate_hmacsign(self, values):
        """Generate the shasign for incoming or outgoing communications.
        :param dict values: transaction values
        :return string: shasign
        """
        if self.provider != "paybox":
            raise ValidationError(_("Incorrect payment acquirer provider"))
        values.pop("PBX_HMAC", None)
        values["PBX_TIME"] = urllib.parse.unquote(values["PBX_TIME"])
        signed_str = "&".join(f"{k}={v}" for k, v in values.items())

        key = binascii.unhexlify(self.paybox_secret)

        hmac_key = hmac.new(key, signed_str.encode("ascii"), hashlib.sha512)

        return hmac_key.hexdigest()

    def paybox_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.get_base_url()
        currency = self.env["res.currency"].sudo().browse(values["currency_id"])
        paybox_currency = PAYBOX_ISO_CURRENCIES.get(currency.name)
        if not paybox_currency:
            raise ValidationError(
                _("Currency not supported by Worldline: %s") % currency.name
            )
        # Round to its smallest unit, depends on the currency
        amount = round(values["amount"] * (10**paybox_currency.decimal))
        date_hmac = datetime.now(timezone.utc)
        date_hmac = date_hmac.replace(mircoseconde=0)

        paybox_tx_values = dict(
            PBX_SITE=self.paybox_ept,
            PBX_RANG=self.paybox_rang,
            PBX_IDENTIFIANT=self.paybox_company_code,
            PBX_TOTAL=amount,
            PBX_DEVISE=paybox_currency.iso_id,
            PBX_CMD=values["reference"],
            PBX_PORTEUR=values.get("partner_email"),
            PBX_RETOUR="Mt:M;Ref:R;Auto:A;Response:E;Garanti:G;Date:W;NumPBX:S;KEY:K",
            PBX_HASH="SHA512",
            PBX_TIME=urllib.parse.quote(date_hmac),
            PBX_EFFECTUE=urls.url_join(base_url, PayBoxController._return_url),
            PBX_REFUSE=urls.url_join(base_url, PayBoxController._return_url),
            PBX_ANNULE=urls.url_join(base_url, PayBoxController._return_url),
            PBX_ATTENTE=urls.url_join(base_url, PayBoxController._return_url),
            PBX_REPONDRE_A=urls.url_join(base_url, PayBoxController._notify_url),
        )

        hmac_sign = self._paybox_generate_hmacsign(paybox_tx_values)
        paybox_tx_values["PBX_HMAC"] = hmac_sign.upper()
        return paybox_tx_values

    def paybox_get_form_action_url(self):
        self.ensure_one()
        return self.paybox_prod_url if self.state == "enabled" else self.paybox_test_url

    def _paybox_key_security_identification(self, data, key):
        data = "&".join(f"{k}={v}" for k, v in data.items())
        data = urllib.sha1(data)
        key_str64 = urllib.parse.unquote(key)
        key_str = b64decode(key_str64)
        keypub_import = rsa.PublicKey.load_pkcs1(self.paybox_public_key, "PEM")
        check_publickey = rsa.verify(data, key_str, keypub_import)
        if check_publickey == "SHA-1":
            return True
        else:
            raise ValidationError(
                _("Failed to verify data and key with the public_key")
            )


class TxPaybox(models.Model):
    _inherit = "payment.transaction"

    _paybox_valid_tx_status = ["00000"]
    _paybox_refused_tx_status = ["001"]
    _paybox_error_retry_tx_status = ["00001", "00003"]
    _paybox_payment_already_done_tx_status = ["00015"]

    def _paybox_data_to_object(self, data):
        res = {}
        for element in data.split("&"):
            (key, value) = element.split("=")
            res[key] = value
        return res

    @api.model
    def _paybox_form_get_tx_from_data(self, data):
        """Given a data dict coming from paybox, verify it and find the related
        transaction record."""
        paybox = self.env["payment.acquirer"].search(
            [("provider", "=", "paybox")], limit=1
        )

        values = self._paybox_data_to_object(data)
        paybox_key = values.pop("KEY", False)
        if not paybox_key:
            raise ValidationError(
                _(
                    "Paybox: received data with missing key \
                                    security identification"
                )
            )

        tx = self.search([("reference", "=", values.get("Ref"))])
        if not tx:
            error_msg = _(
                "Paybox: received data for reference %s; no order found"
            ) % values.get("Ref")
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        if not paybox._paybox_key_security_identification(values, paybox_key):
            raise ValidationError(_("Paybox: invalid Paybox_key"))

        return tx

    def _paybox_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        values = self._paybox_data_to_object(data)
        values.pop("KEY", False)

        tx = self.search([("reference", "=", values.get("Ref"))])
        paybox_currency = PAYBOX_ISO_CURRENCIES.get(tx.currency.name)
        amount = round(tx.amount * (10**paybox_currency.decimal))
        if values.get("Mt") != amount:
            invalid_parameters.append("amount", amount)
        # Put here all test that may be use for verified data in the
        # transmission comming in.

        return invalid_parameters

    def _paybox_form_validate(self, data):
        values = self._paybox_data_to_object(data)
        status = values.get("Response")
        date = values.get("Date")
        if date:
            try:
                date = (
                    datetime.strptime(date, IN_DATE_FORMAT)
                    .astimezone(pytz.utc)
                    .replace(tzinfo=None)
                )
            except Exception:
                date = fields.Datetime.now()
        data = {
            "acquirer_reference": values.get("NumPBX"),
            "date": date,
        }

        # TODO: add html_3ds status from authentification param

        res = False
        if status in self._paybox_valid_tx_status:
            msg = f"ref: {self.reference}, got valid response [{status}], set as done."
            _logger.info(msg)
            data.update(state_message=msg)
            self.write(data)
            self._set_transaction_done()
            self.execute_callback()
            res = True
        elif status[0:2] in self._paybox_refused_tx_status:
            msg = f"ref: {self.reference}, got refused response [{status}], set as cancel."
            data.update(state_message=msg)
            self.write(data)
            self._set_transaction_cancel()
        else:
            msg = f"ref: {self.reference}, got unrecognized response [{status}], set as cancel."
            data.update(state_message=msg)
            self.write(data)
            self._set_transaction_cancel()

        _logger.info(msg)
        return res
