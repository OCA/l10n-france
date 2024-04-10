# Copyright 2024 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from encodings import hex_codec
from hashlib import sha1
from hmac import HMAC

from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
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

    def _monetico_generate_shasign(self, values):
        """Generate the shasign for incoming or outgoing communications.

        Note: self.ensure_one()

        :param str data: The data to use to generate the shasign
        :return: shasign
        :rtype: str
        """
        self.ensure_one()
        signed_items = dict(sorted(values.items()))
        signed_items.pop("MAC", None)
        signed_str = "*".join(f"{k}={v}" for k, v in signed_items.items())

        hmac = HMAC(self._get_monetico_sign_key(), None, sha1)
        hmac.update(signed_str.encode("iso8859-1"))

        return hmac.hexdigest()

    def _monetico_form_presign_hook(self, values):
        """Hook to modify the values of the form before generating the shasign."""
        return values
