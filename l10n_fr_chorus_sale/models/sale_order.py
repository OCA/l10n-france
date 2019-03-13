# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api, _
from openerp.exceptions import Warning as UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    public_market_id = fields.Many2one(
        'public.market', string='Public Market', ondelete='restrict',
        track_visibility='onchange', readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    invoice_transmit_method_id = fields.Many2one(
        related='partner_invoice_id.customer_invoice_transmit_method_id',
        string='Invoice Transmission Method', readonly=True)
    invoice_transmit_method_code = fields.Char(
        related='partner_invoice_id.customer_invoice_transmit_method_id.code',
        readonly=True)

    @api.multi
    def action_button_confirm(self):
        '''Check validity of Chorus orders'''
        self.ensure_one()
        if self.invoice_transmit_method_code == 'fr-chorus':
            cpartner = self.partner_invoice_id.commercial_partner_id
            if not cpartner.siren or not cpartner.nic:
                raise UserError(_(
                    "Missing SIRET on partner '%s'. "
                    "This information is required for Chorus invoices.")
                    % cpartner.name)
            if (
                    cpartner.fr_chorus_required in
                    ('service', 'service_and_engagement') and
                    not self.partner_invoice_id.parent_id):
                raise UserError(_(
                    "Partner '%s' is configured as "
                    "Service Code required for Chorus, so you must "
                    "select a contact as invoicing address for the order %s.")
                    % (cpartner.name, self.name))
            if (
                    cpartner.fr_chorus_required in
                    ('service', 'service_and_engagement') and
                    not self.partner_invoice_id.fr_chorus_service_code):
                raise UserError(_(
                    "Missing 'Chorus Service Code' on contact '%s' of "
                    "customer '%s' which is configured as "
                    "Service Code required for Chorus.")
                    % (self.partner_invoice_id.name, cpartner.name))
            if (
                    cpartner.fr_chorus_required in
                    ('engagement', 'service_and_engagement') and
                    not self.client_order_ref):
                raise UserError(_(
                    "The field 'Reference/Description' of order %s should "
                    "contain the engagement number because customer '%s' is "
                    "configured as Engagement required for Chorus.")
                    % (self.name, cpartner.name))
            if (
                    cpartner.fr_chorus_required ==
                    'service_or_engagement' and (
                    not self.client_order_ref or
                    not self.partner_invoice_id.parent_id)):
                raise UserError(_(
                    "Partner '%s' is configured as "
                    "Service or Engagement required for Chorus but "
                    "there is no engagement number in the field "
                    "'Reference/Description' of order %s and the invoice "
                    "address is not a contact (Service Codes can only be "
                    "configured on contacts)") % (cpartner.name, self.name))
            if (
                    cpartner.fr_chorus_required ==
                    'service_or_engagement' and (
                    not self.client_order_ref or
                    not self.partner_invoice_id.fr_chorus_service_code)):
                raise UserError(_(
                    "Partner '%s' is configured as "
                    "Service or Engagement required for Chorus but "
                    "there is no Engagement number in the field "
                    "'Reference/Description' of order %s and the "
                    "'Chorus Service Code' is not configured "
                    "on contact '%s'") % (
                    cpartner.name, self.name, self.partner_invoice_id.name))
        return super(SaleOrder, self).action_button_confirm()

    @api.model
    def _prepare_invoice(self, order, lines):
        vals = super(SaleOrder, self)._prepare_invoice(order, lines)
        if order.public_market_id:
            vals['public_market_id'] = order.public_market_id.id
        return vals
