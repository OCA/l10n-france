# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_move_create(self):
        '''Check validity of Chorus invoices'''
        for inv in self:
            if inv.transmit_method_code == 'fr-chorus':
                for tline in inv.tax_line_ids:
                    if tline.tax_id and not tline.tax_id.unece_due_date_code:
                        raise UserError(_(
                            "Unece Due Date not configured on tax '%s'. This "
                            "information is required for Chorus invoices.")
                            % tline.tax_id.display_name)
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
                        "there is no engagement number in the field "
                        "'Reference/Description' and the "
                        "'Chorus Service Code' is not configured "
                        "on contact '%s'") % (
                        cpartner.name, inv.partner_id.name))
        return super(AccountInvoice, self).action_move_create()
