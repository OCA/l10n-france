# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
logger = logging.getLogger(__name__)


class ChorusFlow(models.Model):
    _name = 'chorus.flow'
    _description = 'Chorus Flow'
    _order = 'id desc'

    name = fields.Char(
        'Flow Ref', readonly=True, copy=False, required=True)
    date = fields.Date(
        'Flow Date', readonly=True, copy=False, required=True)
    attachment_id = fields.Many2one(
        'ir.attachment', string='File Sent to Chorus',
        readonly=True, copy=False)
    status = fields.Char(
        string='Flow Status', readonly=True, copy=False)
    status_date = fields.Datetime(
        string='Last Status Update', readonly=True, copy=False)
    syntax = fields.Selection(
        [], string='Flow Syntax', readonly=True, copy=False, required=True)
    notes = fields.Text(string='Notes', readonly=True, copy=False)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env['res.company']._company_default_get(
            'chorus.flow'))
    invoice_identifiers = fields.Boolean(
        compute='_compute_invoice_identifiers', readonly=True, store=True)
    invoice_ids = fields.One2many(
        'account.invoice', 'chorus_flow_id', string='Invoices', readonly=True)

    @api.depends('invoice_ids.chorus_identifier')
    def _compute_invoice_identifiers(self):
        for flow in self:
            flow.invoice_identifiers = all(
                [inv.chorus_identifier for inv in flow.invoice_ids])

    def name_get(self):
        res = []
        for flow in self:
            name = flow.name
            if flow.status:
                name = u'%s (%s)' % (name, flow.status)
            res.append((flow.id, name))
        return res

    @api.model
    def syntax_odoo2chorus(self):
        return {}

    def chorus_api_consulter_cr(self, api_params, session=None):
        self.ensure_one()
        syntax_flux = self.syntax_odoo2chorus()[self.syntax]
        payload = {
            'numeroFluxDepot': self.name,
            'dateDepot': self.date,
            'syntaxeFlux': syntax_flux,
            }
        answer, session = self.env['chorus.api'].chorus_post(
            api_params, 'transverses/consulterCR', payload, session=session)
        res = {}
        if answer:
            res = {
                'status': answer.get('etatCourantFlux'),
                'notes': answer.get('libelle'),
                }
        return (res, session)

    def update_flow_status(self):
        '''Called by a button on the flow or by cron'''
        logger.info('Start to update chorus flow status')
        company2api = {}
        raise_if_ko = self._context.get('chorus_raise_if_ko', True)
        flows = []
        for flow in self:
            company = flow.company_id
            if company not in company2api:
                api_params = company.chorus_get_api_params(
                    raise_if_ko=raise_if_ko)
                if not api_params:
                    continue
                company2api[company] = api_params
            flows.append(flow)
        session = None
        for flow in flows:
            api_params = company2api[flow.company_id]
            flow_vals, session = flow.chorus_api_consulter_cr(
                api_params, session=session)
            if flow_vals:
                flow_vals['status_date'] = fields.Datetime.now()
                flow.write(flow_vals)
        logger.info('End of the update of chorus flow status')

    def chorus_api_rechercher_fournisseur(self, api_params, session=None):
        self.ensure_one()
        url_path = 'factures/rechercher/fournisseur'
        payload = {
            "numeroFluxDepot": self.name,
            }
        answer, session = self.env['chorus.api'].chorus_post(
            api_params, url_path, payload)
        invnum2chorus = {}
        # key = odoo invoice number, value = {} to write on odoo invoice
        if (
                answer.get('listeFactures') and
                isinstance(answer['listeFactures'], list)):
            for cinv in answer['listeFactures']:
                if (
                        cinv.get('numeroFacture') and
                        cinv.get('identifiantFactureCPP')):
                    invnum2chorus[cinv['numeroFacture']] = {
                        'chorus_identifier': cinv['identifiantFactureCPP'],
                        }
                    if cinv.get('statut'):
                        invnum2chorus[cinv['numeroFacture']].update({
                            'chorus_status': cinv['statut'],
                            'chorus_status_date': fields.Datetime.now(),
                            })
        return invnum2chorus, session

    def get_invoice_identifiers(self):
        """Called by a button or cron"""
        logger.info('Start to get chorus invoice identifiers')
        company2api = {}
        raise_if_ko = self._context.get('chorus_raise_if_ko', True)
        flows = []
        for flow in self:
            if flow.status != 'IN_INTEGRE':
                if raise_if_ko:
                    raise UserError(_(
                        "On flow %s, the status is not 'IN_INTEGRE'")
                        % (flow.name, flow.status))
                logger.warning(
                    "Skipping flow %s: chorus flow status should be "
                    "IN_INTEGRE but current value is %s", flow.name,
                    flow.status)
                continue
            if flow.invoice_identifiers:
                if raise_if_ko:
                    raise UserError(_(
                        "The Chorus Invoice Identifiers are already set "
                        "for flow %s") % flow.name)
                logger.warning(
                    "Skipping flow %s: chorus identifiers already set",
                    flow.name)
                continue
            company = flow.company_id
            if company not in company2api:
                api_params = company.chorus_get_api_params(
                    raise_if_ko=raise_if_ko)
                if not api_params:
                    continue
                company2api[company] = api_params
            flows.append(flow)
        session = None
        for flow in flows:
            api_params = company2api[flow.company_id]
            invnum2chorus, session = flow.chorus_api_rechercher_fournisseur(
                api_params, session=session)
            if invnum2chorus:
                for inv in flow.invoice_ids:
                    if inv.number in invnum2chorus:
                        inv.write(invnum2chorus[inv.number])
        logger.info('End of the retrieval of chorus invoice identifiers')

    @api.model
    def chorus_cron(self):
        self = self.with_context(chorus_raise_if_ko=False)
        logger.info('Start Chorus flow cron')
        to_update_flows = self.search([
            ('status', '=', False)])
        to_update_flows.update_flow_status()
        get_identifiers_flows = self.search([
            ('status', '=', 'IN_INTEGRE'),
            ('invoice_identifiers', '=', False)])
        get_identifiers_flows.get_invoice_identifiers()
        invoices_update_invoice_status = self.env['account.invoice'].search([
            ('state', 'in', ('open', 'paid')),
            ('type', 'in', ('out_invoice', 'out_refund')),
            ('transmit_method_code', '=', 'fr-chorus'),
            ('chorus_identifier', '!=', False),
            ('chorus_status', '!=', 'MANDATEE')])
        invoices_update_invoice_status.chorus_update_invoice_status()
        logger.info('End Chorus flow cron')
