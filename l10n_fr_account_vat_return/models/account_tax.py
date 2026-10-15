# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools import float_compare, float_is_zero


class AccountTax(models.Model):
    _inherit = "account.tax"

    fr_vat_autoliquidation = fields.Selection(
        [
            ("total", "Total"),
            ("partial", "Partial"),
        ],
        compute="_compute_fr_vat_autoliquidation",
        store=True,
        string="Autoliquidation",
    )

    @api.depends(
        "type_tax_use",
        "amount_type",
        "amount",
        "invoice_repartition_line_ids.repartition_type",
        "invoice_repartition_line_ids.account_id",
        "invoice_repartition_line_ids.factor_percent",
        "refund_repartition_line_ids.repartition_type",
        "refund_repartition_line_ids.account_id",
        "refund_repartition_line_ids.factor_percent",
    )
    def _compute_fr_vat_autoliquidation(self):
        for tax in self:
            autoliquidation = False
            if (
                tax.type_tax_use == "purchase"
                and tax.amount_type == "percent"
                and not float_is_zero(tax.amount, precision_digits=2)
            ):
                # We only analyse invoice repartition lines. Refund
                # repartition lines should be the same as invoice repartition lines.
                # If it's not the case, it will raise in manual2auto()
                lines = tax.invoice_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == "tax"
                    and x.account_id
                    and x.factor_percent
                )
                if len(lines) == 2:
                    total = 0.0
                    signs = set()
                    for line in lines:
                        total += line.factor_percent
                        factor_percent_fc = float_compare(
                            line.factor_percent, 0, precision_digits=2
                        )
                        if factor_percent_fc > 0:
                            signs.add("positive")
                        elif factor_percent_fc < 0:
                            signs.add("negative")
                    if len(signs) == 2:
                        autoliquidation = "partial"
                        if float_is_zero(total, precision_digits=2):
                            autoliquidation = "total"
            tax.fr_vat_autoliquidation = autoliquidation
