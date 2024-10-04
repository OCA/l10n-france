# Copyright 2024 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import json
import logging
from base64 import b64encode
from datetime import datetime
from encodings import hex_codec
from hashlib import sha1
from hmac import HMAC

import pytz
from werkzeug import urls

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare
from odoo.tools.translate import _

from odoo.addons.payment.models.payment_acquirer import ValidationError

from ..controllers.main import MoneticoController

_logger = logging.getLogger(__name__)

OUT_DATE_FORMAT = "%d/%m/%Y:%H:%M:%S"
IN_DATE_FORMAT = "%d/%m/%Y_a_%H:%M:%S"


class AcquirerMonetico(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(
        selection_add=[("monetico", "Monetico")], ondelete={"monetico": "set default"}
    )
    monetico_ept = fields.Char(
        "EPT number", required_if_provider="monetico", groups="base.group_user"
    )
    monetico_company_code = fields.Char(
        "Company code",
        required_if_provider="monetico",
    )
    monetico_secret = fields.Char(
        "Secret Key", required_if_provider="monetico", groups="base.group_user"
    )
    monetico_test_url = fields.Char(
        "Test url",
        required_if_provider="monetico",
        default="https://p.monetico-services.com/test/paiement.cgi",
    )
    monetico_prod_url = fields.Char(
        "Production url",
        required_if_provider="monetico",
        default="https://p.monetico-services.com/paiement.cgi",
    )
    monetico_version = fields.Char(
        "Interface Version", required_if_provider="monetico", default="3.0"
    )

    def _get_monetico_sign_key(self):
        key = self.monetico_secret
        hexStrKey = key[0:38]
        hexFinal = key[38:40] + "00"

        cca0 = ord(hexFinal[0:1])

        if cca0 > 70 and cca0 < 97:
            hexStrKey += chr(cca0 - 23) + hexFinal[1:2]
        elif hexFinal[1:2] == "M":
            hexStrKey += hexFinal[0:1] + "0"
        else:
            hexStrKey += hexFinal[0:2]

        c = hex_codec.Codec()
        hexStrKey = c.decode(hexStrKey)[0]

        return hexStrKey

    def _get_monetico_contexte_commande(self, values):
        billing_country = values.get("billing_partner_country")
        billing_country = billing_country.code if billing_country else None
        billing_state = values.get("billing_partner_state")
        billing_state = billing_state.code if billing_state else None

        billing = dict(
            firstName=values.get("billing_partner_first_name"),
            lastName=values.get("billing_partner_last_name"),
            mobilePhone=None,  # TODO Format correctly values.get("billing_partner_phone"),
            addressLine1=values.get("billing_partner_address"),
            city=values.get("billing_partner_city"),
            postalCode=values.get("billing_partner_zip"),
            country=billing_country,
            email=values.get("billing_partner_email"),
            stateOrProvince=billing_state,
        )

        # shipping = dict(
        #     firstName="Ada",
        #     lastName="Lovelace",
        #     addressLine1="101 Rue de Roisel",
        #     city="Y",
        #     postalCode="80190",
        #     country="FR",
        #     email="ada@some.tld",
        #     phone="+33-612345678",
        #     shipIndicator="billing_address",
        #     deliveryTimeframe="two_day",
        #     firstUseDate="2017-01-25",
        #     matchBillingAddress=True,
        # )

        # client = dict(
        #     email="ada@some.tld",
        #     birthCity="Londre",
        #     birthPostalCode="W1",
        #     birthCountry="GB",
        #     birthdate="2000-12-10",
        # )

        return dict(billing=billing)

    def _monetico_generate_shasign(self, values):
        """Generate the shasign for incoming or outgoing communications.
        :param dict values: transaction values
        :return string: shasign
        """
        if self.provider != "monetico":
            raise ValidationError(_("Incorrect payment acquirer provider"))
        signed_items = dict(sorted(values.items()))
        signed_items.pop("MAC", None)
        signed_str = "*".join(f"{k}={v}" for k, v in signed_items.items())

        hmac = HMAC(self._get_monetico_sign_key(), None, sha1)
        hmac.update(signed_str.encode("iso8859-1"))

        return hmac.hexdigest()

    def _monetico_form_presign_hook(self, values):
        return values

    def monetico_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.get_base_url()
        currency = self.env["res.currency"].sudo().browse(values["currency_id"])
        amount = f"{values['amount']:.2f}{currency.name}"

        lang = values.get("partner_lang")
        if lang:
            lang = lang.split("_")[0].upper()

        if lang not in ["DE", "EN", "ES", "FR", "IT", "JA", "NL", "PT", "SV"]:
            lang = "FR"

        monetico_tx_values = dict(
            TPE=self.monetico_ept,
            contexte_commande=b64encode(
                json.dumps(self._get_monetico_contexte_commande(values)).encode("utf-8")
            ).decode("utf-8"),
            date=fields.Datetime.now().strftime(OUT_DATE_FORMAT),
            lgue=lang,
            mail=values.get("partner_email"),
            montant=amount,
            reference=values["reference"],
            societe=self.monetico_company_code,
            url_retour_ok=urls.url_join(base_url, MoneticoController._return_url),
            url_retour_err=urls.url_join(base_url, MoneticoController._return_url),
            version=self.monetico_version,
        )

        monetico_tx_values = self._monetico_form_presign_hook(monetico_tx_values)

        shasign = self._monetico_generate_shasign(monetico_tx_values)
        monetico_tx_values["MAC"] = shasign
        return monetico_tx_values

    def monetico_get_form_action_url(self):
        self.ensure_one()
        return (
            self.monetico_prod_url
            if self.state == "enabled"
            else self.monetico_test_url
        )


class TxMonetico(models.Model):
    _inherit = "payment.transaction"

    _monetico_valid_tx_status = ["paiement", "payetest"]
    _monetico_refused_tx_status = ["annulation"]

    @api.model
    def _monetico_form_get_tx_from_data(self, data):
        """Given a data dict coming from monetico, verify it and find the related
        transaction record."""
        values = dict(data)
        shasign = values.pop("MAC", False)
        if not shasign:
            raise ValidationError(_("Monetico: received data with missing MAC"))

        tx = self.search([("reference", "=", values.get("reference"))])
        if not tx:
            error_msg = _(
                "Monetico: received data for reference %s; no order found"
            ) % values.get("reference")
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        if shasign.upper() != tx.acquirer_id._monetico_generate_shasign(data).upper():

            raise ValidationError(_("Monetico: invalid shasign"))

        return tx

    def _monetico_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        amount = data.get("montant", data.get("montantestime"))
        # currency and amount should match
        amount, currency = amount[:-3], amount[-3:]
        if currency != self.currency_id.name:
            invalid_parameters.append(("currency", currency, self.currency_id.name))

        if float_compare(float(amount), self.amount, 2) != 0:
            invalid_parameters.append(("amount", amount, "%.2f" % self.amount))

        return invalid_parameters

    def _monetico_form_validate(self, data):
        status = data.get("code-retour").lower()
        date = data.get("date")
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
            "acquirer_reference": data.get("reference"),
            "date": date,
        }

        # TODO: add html_3ds status from authentification param

        res = False
        if status in self._monetico_valid_tx_status:
            msg = f"ref: {self.reference}, got valid response [{status}], set as done."
            _logger.info(msg)
            data.update(state_message=msg)
            self.write(data)
            self._set_transaction_done()
            self.execute_callback()
            res = True
        elif status in self._monetico_refused_tx_status:
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
