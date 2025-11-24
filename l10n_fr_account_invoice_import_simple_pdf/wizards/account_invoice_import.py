# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountInvoiceImport(models.TransientModel):
    _inherit = "account.invoice.import"

    @api.model
    def _simple_pdf_keyword_fields(self):
        field_dict = super()._simple_pdf_keyword_fields()
        field_dict["siren"] = "SIREN"
        return field_dict
