# Copyright 2024 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import json
import logging
from base64 import b64encode

from werkzeug import urls

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils

from ..controllers.main import MoneticoController

_logger = logging.getLogger(__name__)

OUT_DATE_FORMAT = "%d/%m/%Y:%H:%M:%S"
IN_DATE_FORMAT = "%d/%m/%Y_a_%H:%M:%S"

RESPONSE_CODES_MAPPING = {
    "done": ["paiement", "payetest"],
    "pending": [],
    "cancel": ["annulation"],
}


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_monetico_contexte_commande(self):
        billing = dict(
            name=self.partner_name or None,
            mobilePhone=self.partner_phone or None,
            addressLine1=self.partner_address or None,
            city=self.partner_city or None,
            postalCode=self.partner_zip or None,
            country=(
                self.partner_id.country_id.code if self.partner_country_id else None
            ),
            email=self.partner_email or None,
            stateOrProvince=(
                self.partner_id.state_id.code if self.partner_state_id else None
            ),
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

    def _get_specific_rendering_values(self, processing_values):
        """Override of payment to return Monetico-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific
                                       processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "monetico":
            return res

        base_url = self.get_base_url()
        amount = payment_utils.to_minor_currency_units(self.amount, self.currency_id)
        amount = f"{amount:.2f}{self.currency_id.name}"

        lang = self.partner_lang
        if lang:
            lang = lang.split("_")[0].upper()

        if lang not in ["DE", "EN", "ES", "FR", "IT", "JA", "NL", "PT", "SV"]:
            lang = "FR"

        monetico_tx_values = dict(
            TPE=self.provider_id.monetico_ept,
            contexte_commande=b64encode(
                json.dumps(self._get_monetico_contexte_commande()).encode("utf-8")
            ).decode("utf-8"),
            date=fields.Datetime.now().strftime(OUT_DATE_FORMAT),
            lgue=lang,
            mail=self.partner_email or None,
            montant=amount,
            reference=self.reference,
            societe=self.provider_id.monetico_company_code,
            url_retour_ok=urls.url_join(base_url, MoneticoController._return_url),
            url_retour_err=urls.url_join(base_url, MoneticoController._return_url),
            version=self.provider_id.monetico_version,
        )
        api_url = (
            self.provider_id.monetico_prod_url
            if self.provider_id.state == "enabled"
            else self.provider_id.monetico_test_url
        )

        monetico_tx_values = self.provider_id._monetico_form_presign_hook(
            monetico_tx_values
        )
        shasign = self.provider_id._monetico_generate_shasign(monetico_tx_values)
        monetico_tx_values["MAC"] = shasign
        monetico_tx_values["api_url"] = api_url
        return monetico_tx_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Override of payment to find the transaction based on Monetico data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != "monetico" or len(tx) == 1:
            return tx

        values = dict(notification_data)
        shasign = values.pop("MAC", False)
        if not shasign:
            raise ValidationError(_("Monetico: received data with missing MAC"))
        reference = values.get("reference")

        tx = self.search(
            [
                ("reference", "=", reference),
                ("provider_code", "=", "monetico"),
            ]
        )
        if not tx:
            raise ValidationError(
                _("Monetico: ")
                + _("No transaction found matching reference %s.", reference)
            )

        return tx

    def _process_notification_data(self, notification_data):
        """Override of payment to process the transaction based on Monetico data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != "monetico":
            return

        self.provider_reference = notification_data.get("reference")

        # TODO: add html_3ds status from authentification param

        response_code = notification_data.get("code-retour").lower()
        if response_code in RESPONSE_CODES_MAPPING["pending"]:
            status = "pending"
            self._set_pending()
        elif response_code in RESPONSE_CODES_MAPPING["done"]:
            status = "done"
            self._set_done()
        elif response_code in RESPONSE_CODES_MAPPING["cancel"]:
            status = "cancel"
            self._set_canceled()
        else:
            status = "error"
            self._set_error(
                _("Unrecognized response received from the payment provider.")
            )
        _logger.info(
            "received data with response %(response)s for transaction "
            "with reference %(ref)s, set "
            "status as '%(status)s'",
            {
                "response": response_code,
                "ref": self.reference,
                "status": status,
            },
        )
