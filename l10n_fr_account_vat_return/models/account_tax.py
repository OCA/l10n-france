# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools import float_is_zero


class AccountTax(models.Model):
    _inherit = "account.tax"

    fr_vat_autoliquidation = fields.Boolean(
        compute="_compute_fr_vat_autoliquidation", store=True, string="Auto-Liquidation"
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
        atrlo = self.env["account.tax.repartition.line"]
        for tax in self:
            autoliquidation = False
            if (
                tax.type_tax_use == "purchase"
                and tax.amount_type == "percent"
                and not float_is_zero(tax.amount, precision_digits=2)
            ):
                autoliquidation = True
                for parent_field in ("invoice_tax_id", "refund_tax_id"):
                    lines = atrlo.search(
                        [
                            (parent_field, "=", tax.id),
                            ("repartition_type", "=", "tax"),
                            ("account_id", "!=", False),
                        ]
                    )
                    if len(lines) != 2:
                        autoliquidation = False
                        break
                    factor_sum = 0.0
                    for line in lines:
                        factor_sum += line.factor_percent
                    if not float_is_zero(factor_sum, precision_digits=2):
                        autoliquidation = False
                        break
            tax.fr_vat_autoliquidation = autoliquidation
