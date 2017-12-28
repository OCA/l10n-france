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

    chorus_flow_ref = fields.Char(
        string='Chorus Flow Ref', readonly=True, copy=False,
        help=u"This field stores the 'Numéro du flux dépôt'.")
    chorus_flow_date = fields.Date(
        string='Chorus Flow Date', readonly=True, copy=False)
    chorus_flow_status = fields.Char(
        string='Chorus Flow Status', readonly=True, copy=False,
        track_visibility='onchange')
    chorus_flow_status_date = fields.Datetime(
        string='Last Chorus Flow Status Update')
    chorus_format = fields.Selection(
        [], string='Chorus Flow Syntax', readonly=True, copy=False)
    chorus_identifier = fields.Integer(
        string='Chorus Invoice Indentifier', readonly=True, copy=False)
    chorus_status = fields.Char(
        string='Chorus Invoice Status', readonly=True, copy=False,
        track_visibility='onchange')
    chorus_status_date = fields.Datetime(
        string='Last Chorus Invoice Status Date')
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

    @api.model
    def chorus_invoiceformat2syntax(self):
        return {}

    def prepare_chorus_deposer_flux_payload(self):
        raise UserError(_(
            "The Chorus Invoice Format '%s' is not supported.")
            % self.company_id.fr_chorus_invoice_format)

    def chorus_api_deposer_flux(self, api_params, session=None):
        self.ensure_one()
        payload = self.prepare_chorus_deposer_flux_payload()
        url_path = 'factures/deposer/flux'
        # url = 'https://chorus-pro.gouv.fr:5443/service/factures/deposer/flux'
        logger.info(
            'Start to send invoice %s ID %d via Chorus %sWS',
            self.number, self.id, api_params['qualif'] and 'QUALIF. ' or '')
        answer, session = self.chorus_post(
            api_params, url_path, payload, session=session)
        res = {
            'chorus_flow_ref': answer.get('numeroFluxDepot'),
            'chorus_flow_date': answer.get('dateDepot'),
            'chorus_format': self.company_id.fr_chorus_invoice_format,
        }
        return (res, session)

    def chorus_send_invoice(self):
        '''Called by the button on the invoice'''
        # The "check" loop
        company2api = {}  # key = company, value = api_params
        for inv in self:
            if inv.state not in ('open', 'paid'):
                raise UserError(_(
                    "The state of invoice %s is not Open nor Paid, so it "
                    "can't be sent through Chorus"))
            company = inv.company_id
            if not company.fr_chorus_invoice_format:
                raise UserError(_(
                    "Chorus Invoice Format is not configured on company %s")
                    % company.display_name)
            if not company.fr_chorus_invoice_format.startswith('xml_'):
                raise UserError(_(
                    'For the moment, the only supported Chorus invoice format '
                    'is XML.'))
            if company not in company2api:
                api_params = company.chorus_get_api_params(raise_if_ko=True)
                company2api[company] = api_params
        # The "do the real work" loop
        # I want a 2nd loop because I don't want a raise in this 2nd loop
        # to avoid a rollback on already sent data
        session = None
        for inv in self:
            api_params = company2api[inv.company_id]
            res, session = inv.chorus_api_deposer_flux(
                api_params, session=session)
            if res and res.get('chorus_flow_ref'):
                inv.write(dict(res, sent=True))

    def chorus_api_consulter_cr(self, api_params, session=None):
        self.ensure_one()
        syntax_flux = self.chorus_invoiceformat2syntax()[self.chorus_format]
        payload = {
            'numeroFluxDepot': self.chorus_flow_ref,
            'dateDepot': self.chorus_flow_date[:10],  # TODO handle timezone
            'syntaxeFlux': syntax_flux,
            }
        answer, session = self.chorus_post(
            api_params, 'transverses/consulterCR', payload, session=session)
        chorus_flow_status = answer.get('etatCourantFlux')
        # if not chorus_flow_status:
        #    answer.get('libelle')
        return (chorus_flow_status, session)

    # TODO : hide button when REJETE ??
    def chorus_update_flow_status(self):
        '''Called by a button on the invoice or by cron'''
        logger.info('Start to update chorus flow status')
        company2api = {}
        raise_if_ko = self._context.get('chorus_raise_if_ko', True)
        invoices = []
        for inv in self:
            if not inv.chorus_flow_ref:
                if raise_if_ko:
                    raise UserError(_(
                        "Missing Chorus Flow Ref on invoice %s") % inv.number)
                logger.warning(
                    "Skipping invoice %s: missing chorus flow ref", inv.number)
                continue
            if not inv.chorus_format:
                if raise_if_ko:
                    raise UserError(_(
                        "Missing Chorus format on invoice %s") % inv.number)
                logger.warning(
                    "Skipping invoice %s: missing chorus format", inv.number)
                continue
            if not inv.chorus_format.startswith('xml_'):
                if raise_if_ko:
                    raise UserError(_(
                        "The Chorus invoice format %s is not supported for "
                        "the moment (invoice %s).")
                        % (inv.chorus_format, inv.number))
                logger.warning(
                    "Skipping invoice %s: unsupported chorus invoice "
                    "format %s", inv.number, inv.chorus_format)
                continue
            if not inv.chorus_flow_date:
                if raise_if_ko:
                    raise UserError(_(
                        "Missing Chorus flow date on invoice %s") % inv.number)
                logger.warning(
                    "Skipping invoice %s: missing Chorus flow date",
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
            chorus_flow_status, session = invoice.chorus_api_consulter_cr(
                api_params, session=session)
            if chorus_flow_status:
                invoice.write({
                    'chorus_flow_status': chorus_flow_status,
                    'chorus_flow_status_date': fields.Datetime.now(),
                })
        logger.info('End of the update of chorus flow status')

    def chorus_api_rechercher_fournisseur(self, api_params, session=None):
        url_path = 'factures/rechercher/fournisseur'
        payload = {
            # 'idUtilisateurCourant': api_params['identifier'],
            "numeroFluxDepot": self.chorus_flow_ref,
            }
        answer, session = self.chorus_post(api_params, url_path, payload)
        vals = {}
        if (
                answer.get('listeFactures') and
                isinstance(answer['listeFactures'], list)):
            for cinv in answer['listeFactures']:
                if (
                        cinv.get('numeroFacture') == self.number and
                        cinv.get('identifiantFactureCPP')):
                    vals = {'chorus_identifier': cinv['identifiantFactureCPP']}
                    if cinv.get('statut'):
                        vals.update({
                            'chorus_status': cinv.get('statut'),
                            'chorus_status_date': fields.Datetime.now(),
                        })
        return vals, session

    def chorus_get_identifier(self):
        """Called by a button or cron"""
        logger.info('Start to get chorus invoice identifiers')
        company2api = {}
        raise_if_ko = self._context.get('chorus_raise_if_ko', True)
        invoices = []
        for inv in self:
            if not inv.chorus_flow_ref:
                if raise_if_ko:
                    raise UserError(_(
                        "Missing Chorus Flow Ref on invoice %s") % inv.number)
                logger.warning(
                    "Skipping invoice %s: missing chorus flow ref", inv.number)
                continue
            if inv.chorus_flow_status != 'IN_INTEGRE':
                if raise_if_ko:
                    raise UserError(_(
                        "On invoice %s, the status of the chorus flow (%s) is "
                        "not 'IN_INTEGRE'")
                        % (inv.number, inv.chorus_flow_status))
                logger.warning(
                    "Skipping invoice %s: chorus flow status should be "
                    "IN_INTEGRE but curent value is %s", inv.number,
                    inv.chorus_flow_status)
                continue
            if inv.chorus_identifier:
                if raise_if_ko:
                    raise UserError(_(
                        "The Chorus Invoice Identifier is already set "
                        "on invoice %s") % inv.number)
                logger.warning(
                    "Skipping invoice %s: chorus identifier already set",
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
            vals, session = invoice.chorus_api_rechercher_fournisseur(
                api_params, session=session)
            if vals:
                invoice.write(vals)
        logger.info('End of the retreival of chorus invoice identifiers')

    def chorus_api_consulter_fournisseur(self, api_params, session=None):
        url_path = 'factures/consulter/fournisseur'
        payload = {
            'identifiantFactureCPP': self.chorus_identifier,
            }
        answer, session = self.chorus_post(
            api_params, url_path, payload, session=session)
        res = False
        if (
                answer.get('facture') and
                answer['facture'].get('identifiantFactureCPP') ==
                self.chorus_identifier and
                answer['facture'].get('statutFacture')):
            res = answer['facture']['statutFacture']
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
            inv_status, session = invoice.chorus_api_consulter_fournisseur(
                api_params, session)
            if inv_status:
                invoice.write({
                    'chorus_status': inv_status,
                    'chorus_status_date': fields.Datetime.now(),
                    })
        logger.info('End of the update of chorus invoice status')

    @api.model
    def chorus_status_cron(self):
        self = self.with_context(chorus_raise_if_ko=False)
        logger.info('Start Chorus API cron')
        base_domain = [
            ('state', 'in', ('open', 'paid')),
            ('type', 'in', ('out_invoice', 'out_refund')),
            ('transmit_method_code', '=', 'fr-chorus')]
        invoices_update_flow_status = self.search(base_domain + [
            ('chorus_flow_ref', '!=', False),
            ('chorus_format', '!=', False),
            ('chorus_flow_date', '!=', False),
            ('chorus_flow_status', '=', False)])
        invoices_update_flow_status.chorus_update_flow_status()
        invoices_get_identifier = self.search(base_domain + [
            ('chorus_flow_status', '=', 'IN_INTEGRE'),
            ('chorus_identifier', '=', False)])
        invoices_get_identifier.chorus_get_identifier()
        invoices_update_invoice_status = self.search(base_domain + [
            ('chorus_identifier', '!=', False)])
        invoices_update_invoice_status.chorus_update_invoice_status()
        logger.info('End Chorus API cron')
