# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # I have to write 2 different fields because invalidation is not
    # the same and we want to allow manual modification on vendor bills
    out_vat_on_payment = fields.Boolean(
        string="VAT on Payment for Customer Invoices",
        compute="_compute_out_vat_on_payment",
        store=True,
    )
    in_vat_on_payment = fields.Boolean(
        compute="_compute_in_vat_on_payment",
        store=True,
        string="VAT on Payment for Vendor Bills",
        states={"draft": [("readonly", False)]},
    )
    fiscal_position_fr_vat_type = fields.Selection(
        related="fiscal_position_id.fr_vat_type",
        store=True,
        string="Fiscal Position Type",
    )

    @api.depends(
        "move_type", "invoice_line_ids.product_id", "invoice_line_ids.price_subtotal"
    )
    def _compute_out_vat_on_payment(self):
        for move in self:
            vat_on_payment = False
            if move.move_type in ("out_invoice", "out_refund"):
                if move.company_id.fr_vat_exigibility == "on_payment":
                    vat_on_payment = True
                elif move.company_id.fr_vat_exigibility == "auto":
                    product_total = 0.0
                    service_total = 0.0
                    for line in move.invoice_line_ids:
                        if not line.display_type and line.product_id:
                            if line.product_id.type == "service":
                                service_total += line.price_subtotal
                            else:
                                product_total += line.price_subtotal
                    if (
                        move.currency_id.compare_amounts(service_total, product_total)
                        > 0
                    ):
                        vat_on_payment = True
            move.out_vat_on_payment = vat_on_payment

    @api.depends("move_type", "commercial_partner_id", "fiscal_position_id")
    def _compute_in_vat_on_payment(self):
        for move in self:
            vat_on_payment = False
            if (
                move.move_type in ("in_invoice", "in_refund")
                and move.commercial_partner_id.supplier_vat_on_payment
                and (
                    not move.fiscal_position_id
                    or move.fiscal_position_id.fr_vat_type in ("france", "france_exo")
                )
            ):
                vat_on_payment = True
            move.in_vat_on_payment = vat_on_payment

    def _collect_tax_cash_basis_values(self):
        return None
