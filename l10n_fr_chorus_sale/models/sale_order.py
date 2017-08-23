# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    invoice_transmit_method_id = fields.Many2one(
        related='partner_invoice_id.customer_invoice_transmit_method_id',
        string='Invoice Transmission Method', readonly=True)
    invoice_transmit_method_code = fields.Char(
        related='partner_invoice_id.customer_invoice_transmit_method_id.code',
        readonly=True)

    @api.multi
    def action_confirm(self):
        '''Check validity of Chorus orders'''
        for order in self.filtered(
                lambda so: so.invoice_transmit_method_code == 'fr-chorus'):
            cpartner = order.partner_invoice_id.commercial_partner_id
            if not cpartner.siren or not cpartner.nic:
                raise UserError(_(
                    "Missing SIRET on partner '%s'. "
                    "This information is required for Chorus invoices.")
                    % cpartner.name)
            if (
                    cpartner.fr_chorus_required in
                    ('service', 'service_and_engagement') and
                    not order.partner_invoice_id.parent_id):
                raise UserError(_(
                    "Partner '%s' is configured as "
                    "Service Code required for Chorus, so you must "
                    "select a contact as invoicing address for the order %s.")
                    % (cpartner.name, order.name))
            if (
                    cpartner.fr_chorus_required in
                    ('service', 'service_and_engagement') and
                    not order.partner_invoice_id.fr_chorus_service_code):
                raise UserError(_(
                    "Missing 'Chorus Service Code' on contact '%s' of "
                    "customer '%s' which is configured as "
                    "Service Code required for Chorus.")
                    % (order.partner_invoice_id.name, cpartner.name))
            if (
                    cpartner.fr_chorus_required in
                    ('engagement', 'service_and_engagement') and
                    not order.client_order_ref):
                raise UserError(_(
                    "The field 'Customer Reference' of order %s should "
                    "contain the engagement number because customer '%s' is "
                    "configured as Engagement required for Chorus.")
                    % (order.name, cpartner.name))
            if (
                    cpartner.fr_chorus_required ==
                    'service_or_engagement' and (
                    not order.client_order_ref or
                    not order.partner_invoice_id.parent_id)):
                raise UserError(_(
                    "Partner '%s' is configured as "
                    "Service or Engagement required for Chorus but "
                    "there is no engagement number in the field "
                    "'Customer Reference' of order %s and the invoice "
                    "address is not a contact (Service Codes can only be "
                    "configured on contacts)") % (cpartner.name, order.name))
            if (
                    cpartner.fr_chorus_required ==
                    'service_or_engagement' and (
                    not order.client_order_ref or
                    not order.partner_invoice_id.fr_chorus_service_code)):
                raise UserError(_(
                    "Partner '%s' is configured as "
                    "Service or Engagement required for Chorus but "
                    "there is no engagement number in the field "
                    "'Customer Reference' of order %s and the "
                    "'Chorus Service Code' is not configured "
                    "on contact '%s'") % (
                    cpartner.name, order.name, order.partner_invoice_id.name))
        return super(SaleOrder, self).action_confirm()
