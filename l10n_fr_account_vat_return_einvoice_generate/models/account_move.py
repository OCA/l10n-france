# Copyright 2024 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_unece_due_date_type_code(self):
        # inherit method from account_einvoice_generate => move to
        if self.move_type in ("out_invoice", "out_refund"):
            if self.out_vat_on_payment:
                tax_exigibility = "on_payment"
            else:
                tax_exigibility = "on_invoice"
            return self.env["account.tax"]._get_unece_code_from_tax_exigibility(
                tax_exigibility
            )
        return super()._get_unece_due_date_type_code()
