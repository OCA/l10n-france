# Copyright 2017-2021 Akretion France (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    invoice_transmit_method_id = fields.Many2one(
        related="partner_invoice_id.customer_invoice_transmit_method_id",
        string="Invoice Transmission Method",
    )
    invoice_transmit_method_code = fields.Char(
        related="partner_invoice_id.customer_invoice_transmit_method_id.code",
    )

    def action_confirm(self):
        """Check validity of Chorus orders"""
        for order in self.filtered(
            lambda so: so.invoice_transmit_method_code == "fr-chorus"
        ):
            order._chorus_validation_checks()
        return super().action_confirm()

    def _chorus_validation_checks(self):
        self.ensure_one()
        self.company_id._chorus_common_validation_checks(
            self, self.partner_invoice_id, self.client_order_ref
        )
