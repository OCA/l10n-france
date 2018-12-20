# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import tarfile
import time
from io import BytesIO
import logging
logger = logging.getLogger(__name__)

CREDIT_TRF_CODES = ('30', '31', '42')


class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice', 'chorus.api']

    chorus_flow_id = fields.Many2one(
        'chorus.flow', string='Chorus Flow', readonly=True, copy=False,
        track_visibility='onchange')
    chorus_identifier = fields.Integer(
        string='Chorus Invoice Indentifier', readonly=True, copy=False,
        track_visibility='onchange')
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
                        not (inv.partner_id.parent_id and
                             inv.partner_id.name and
                             inv.partner_id.fr_chorus_service_id and
                             inv.partner_id.fr_chorus_service_id.active)):
                    raise UserError(_(
                        "Partner '%s' is configured as Service required for "
                        "Chorus, so you must select a contact as customer "
                        "for the invoice and this contact should have a name "
                        "and a Chorus service and the Chorus service must "
                        "be active.") % cpartner.name)
                if (
                        cpartner.fr_chorus_required in
                        ('engagement', 'service_and_engagement') and
                        not inv.name):
                    raise UserError(_(
                        "Partner '%s' is configured as "
                        "Engagement required for Chorus, so the "
                        "field 'Reference/Description' must contain "
                        "an engagement number.") % cpartner.name)
                if (
                        cpartner.fr_chorus_required ==
                        'service_or_engagement' and
                        not inv.name and
                        not (
                        inv.partner_id.parent_id and
                        inv.partner_id.name and
                        inv.partner_id.fr_chorus_service_id)):
                        raise UserError(_(
                            "Partner '%s' is configured as "
                            "'Service or Engagement' required for Chorus but "
                            "there is no engagement number in the field "
                            "'Reference/Description' and the customer of the "
                            "invoice is not correctly configured as a service "
                            "(should be a contact with a Chorus service "
                            "and a name).") % cpartner.name)
                if not self.payment_mode_id:
                    raise UserError(_(
                        "Missing Payment Mode. This "
                        "information is required for Chorus."))
                payment_means_code = self.payment_mode_id.payment_method_id.\
                    unece_code or '30'
                partner_bank_id =\
                    self.partner_bank_id or (
                        self.payment_mode_id.bank_account_link == 'fixed' and
                        self.payment_mode_id.fixed_journal_id.bank_account_id)
                if payment_means_code in CREDIT_TRF_CODES:
                    if not partner_bank_id:
                        raise UserError(_(
                            "Missing bank account information for payment. "
                            "For that, you have two options: either the "
                            "payment mode of the invoice should have "
                            "'Link to Bank Account' = "
                            "'fixed' and the related bank journal should have "
                            "a 'Bank Account' set, or the field "
                            "'Bank Account' should be set on the customer "
                            "invoice."
                            ))
                    if partner_bank_id.acc_type != 'iban':
                        raise UserError(_(
                            "Chorus only accepts IBAN. But the bank account "
                            "'%s' is not an IBAN.")
                            % partner_bank_id.acc_number)
        return super(AccountInvoice, self).action_move_create()

    def chorus_get_invoice(self, chorus_invoice_format):
        self.ensure_one()
        return False

    def prepare_chorus_deposer_flux_payload(self):
        if not self[0].company_id.fr_chorus_invoice_format:
            raise UserError(_(
                "The Chorus Invoice Format is not configured on the "
                "Accounting Configuration page of company '%s'")
                % self[0].company_id.display_name)
        chorus_invoice_format = self[0].company_id.fr_chorus_invoice_format
        short_format = chorus_invoice_format[4:]
        file_extension = chorus_invoice_format[:3]
        syntaxe_flux = self.env['chorus.flow'].syntax_odoo2chorus()[
            chorus_invoice_format]
        if len(self) == 1:
            chorus_file_content = self.chorus_get_invoice(
                chorus_invoice_format)
            filename = '%s_chorus_facture_%s.%s' % (
                short_format,
                self.number.replace('/', '-'),
                file_extension)
        else:
            filename = '%s_chorus_lot_factures.tar.gz' % short_format
            tarfileobj = BytesIO()
            with tarfile.open(fileobj=tarfileobj, mode='w:gz') as tar:
                for inv in self:
                    xml_string = inv.chorus_get_invoice(chorus_invoice_format)
                    xmlfileio = BytesIO(xml_string)
                    xmlfilename =\
                        '%s_chorus_facture_%s.%s' % (
                            short_format,
                            inv.number.replace('/', '-'),
                            file_extension)
                    tarinfo = tarfile.TarInfo(name=xmlfilename)
                    tarinfo.size = len(xml_string)
                    tarinfo.mtime = int(time.time())
                    tar.addfile(tarinfo=tarinfo, fileobj=xmlfileio)
                tar.close()
            tarfileobj.seek(0)
            chorus_file_content = tarfileobj.read()
        payload = {
            'fichierFlux': chorus_file_content.encode('base64'),
            'nomFichier': filename,
            'syntaxeFlux': syntaxe_flux,
            'avecSignature': False,
            }
        return payload

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
