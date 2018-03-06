# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice', 'chorus.api']

    chorus_flow_id = fields.Many2one(
        'chorus.flow', string='Chorus Flow', readonly=True, copy=False)
    chorus_identifier = fields.Integer(
        string='Chorus Invoice Indentifier', readonly=True, copy=False)
    chorus_status = fields.Char(
        string='Chorus Invoice Status', readonly=True, copy=False,
        track_visibility='onchange')
    chorus_status_date = fields.Datetime(
        string='Last Chorus Invoice Status Date', readonly=True, copy=False)
    # M2O Link to attachment to get the file that has really been sent ?

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

    def prepare_chorus_deposer_flux_payload(self):
        raise UserError(_(
            "The Chorus Invoice Format '%s' is not supported.")
            % self.company_id.fr_chorus_invoice_format)

    def chorus_api_consulter_historique(self, api_params, session=None):
        url_path = 'factures/consulter/historique'
        payload = {
            'idFacture': self.chorus_identifier,
            }
        answer, session = self.chorus_post(
            api_params, url_path, payload, session=session)
        res = False
        if (
                answer.get('idFacture') and
                answer['idFacture'] == self.chorus_identifier and
                answer.get('statutCourantCode')):
            res = answer['statutCourantCode']
        return (res, session)

    def chorus_update_invoice_status(self):
        '''Called by a button on the invoice or by cron'''
        logger.info('Start to update chorus invoice status')
        company2api = {}
        raise_if_ko = self._context.get('chorus_raise_if_ko', True)
        invoices = []
        for inv in self:
            if not inv.chorus_identifier:
                if raise_if_ko:
                    raise UserError(_(
                        "Missing Chorus Invoice Identifier on invoice '%s'")
                        % inv.display_name)
                logger.warning(
                    'Skipping invoice %s: missing chorus invoice identifier',
                    inv.number)
                continue
            company = inv.company_id
            if company not in company2api:
                api_params = company.chorus_get_api_params(
                    raise_if_ko=raise_if_ko)
                if not api_params:
                    continue
                company2api[company] = api_params
            invoices.append(inv)
        session = None
        for invoice in invoices:
            api_params = company2api[invoice.company_id]
            inv_status, session = invoice.chorus_api_consulter_historique(
                api_params, session)
            if inv_status:
                invoice.write({
                    'chorus_status': inv_status,
                    'chorus_status_date': fields.Datetime.now(),
                    })
        logger.info('End of the update of chorus invoice status')
