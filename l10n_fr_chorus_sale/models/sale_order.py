# Copyright 2017-2021 Akretion France (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # The related field below should be native... I hope we won't have conflict issues
    # if another module defines the same related field.
    invoice_sending_method = fields.Selection(
        related="partner_id.commercial_partner_id.invoice_sending_method", store=True
    )
    chorus_service_code = fields.Char(
        related="partner_invoice_id.fr_chorus_service_id.code",
        string="Chorus Service Code",
        store=True,
    )

    def action_confirm(self):
        """Check validity of Chorus orders"""
        for order in self.filtered(
            lambda x: x.partner_invoice_id.commercial_partner_id.invoice_sending_method
            == "fr_chorus"
        ):
            order._chorus_validation_checks()
        return super().action_confirm()

    def _get_chorus_service(self):
        self.ensure_one()
        return self.partner_invoice_id.fr_chorus_service_id

    def _chorus_validation_checks(self):
        self.ensure_one()
        self.company_id._chorus_common_validation_checks(
            self,
            self.partner_invoice_id,
            self.client_order_ref,
            self._get_chorus_service(),
        )
