# Copyright 2021-2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    fr_vat_type = fields.Selection(
        "_get_fr_vat_type_sel",
        string="Type",
        help="This field is used by the French VAT return module",
    )

    @api.model
    def _get_fr_vat_type_sel(self):
        sel = [
            ("france", "France"),
            ("france_vendor_vat_on_payment", "France Vendor VAT on Payment"),
            ("intracom_b2b", "Intra-EU B2B"),
            ("intracom_b2c", "Intra-EU B2C over 10k€ limit"),
            ("extracom", "Extra-EU"),
            ("france_exo", "France Exonerated"),
        ]
        return sel
