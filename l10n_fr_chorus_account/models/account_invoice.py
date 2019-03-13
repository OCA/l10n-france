# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api, _
from openerp.exceptions import Warning as UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    public_market_id = fields.Many2one(
        'public.market', string='Public Market', ondelete='restrict',
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange')

    @api.multi
    def action_move_create(self):
        '''Check validity of Chorus invoices'''
        for inv in self:
            if inv.transmit_method_code == 'fr-chorus':
                if not inv.company_id.fr_vat_scheme:
                    raise UserError(_(
                        "French VAT Scheme not configured on company '%s'. "
                        "This information is required for Chorus invoices.")
                        % inv.company_id.name)
                cpartner = inv.commercial_partner_id
                if not cpartner.siren or not cpartner.nic:
                    raise UserError(_(
                        "Missing SIRET on partner '%s'. "
                        "This information is required for Chorus invoices.")
                        % cpartner.name)
                if (
                        cpartner.fr_chorus_required in
                        ('service', 'service_and_engagement') and
                        not inv.partner_id.parent_id):
                    raise UserError(_(
                        "Partner '%s' is configured as "
                        "Service Code required for Chorus, so you must "
                        "select a contact as customer for the invoice.")
                        % cpartner.name)
                if (
                        cpartner.fr_chorus_required in
                        ('service', 'service_and_engagement') and
                        not inv.partner_id.fr_chorus_service_code):
                    raise UserError(_(
                        "Missing 'Chorus Service Code' on contact '%s' of "
                        "customer '%s' which is configured as "
                        "Service Code required for Chorus.")
                        % (inv.partner_id.name, cpartner.name))
                if (
                        cpartner.fr_chorus_required in
                        ('engagement', 'service_and_engagement') and
                        not inv.name):
                    raise UserError(_(
                        "The field 'Reference/Description' should contain "
                        "the engagement number because customer '%s' is "
                        "configured as Engagement required for Chorus.")
                        % cpartner.name)
                if (
                        cpartner.fr_chorus_required ==
                        'service_or_engagement' and (
                        not inv.name or
                        not inv.partner_id.parent_id)):
                    raise UserError(_(
                        "Partner '%s' is configured as "
                        "Service or Engagement required for Chorus but "
                        "there is no engagement number in the field "
                        "'Reference/Description' and the customer "
                        "is not a contact (Service Codes can only be "
                        "configured on contacts)") % cpartner.name)
                if (
                        cpartner.fr_chorus_required ==
                        'service_or_engagement' and (
                        not inv.name or
                        not inv.partner_id.fr_chorus_service_code)):
                    raise UserError(_(
                        "Partner '%s' is configured as "
                        "Service or Engagement required for Chorus but "
                        "there is no Engagement number in the field "
                        "'Reference/Description' and the "
                        "'Chorus Service Code' is not configured "
                        "on contact '%s'") % (
                        cpartner.name, inv.partner_id.name))
        return super(AccountInvoice, self).action_move_create()
