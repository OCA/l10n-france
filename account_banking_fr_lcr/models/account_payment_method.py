# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    fr_lcr_use_crlf = fields.Boolean(
        string="Use CRLF in generated CFONB file",
        help="""Enable usage of CRLF ('\\r\\n') within generated CFONB files.
        Only used for  creation of French LCR CFONB fileds.
        [By default: True]""",
        default=True,
    )

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res["fr_lcr"] = {
            "mode": "multi",
            "domain": [("type", "=", "bank")],
            "currency_id": self.env.ref("base.EUR").id,
        }
        return res
