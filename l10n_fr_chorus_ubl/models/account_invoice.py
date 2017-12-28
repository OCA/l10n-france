# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    chorus_format = fields.Selection(
        selection_add=[('xml_ubl', 'UBL XML')])

    def generate_ubl_xml_string(self, version='2.1'):
        self.ensure_one()
        if self.transmit_method_code == 'fr-chorus':
            self = self.with_context(fr_chorus=True)
        return super(AccountInvoice, self).generate_ubl_xml_string(
            version=version)

    def _ubl_get_contract_document_reference_dict(self):
        self.ensure_one()
        cdr_dict = super(AccountInvoice, self).\
            _ubl_get_contract_document_reference_dict()
        if self.agreement_id:
            cdr_dict[u'Marché public'] = self.agreement_id.code
        return cdr_dict

    @api.model
    def chorus_invoiceformat2syntax(self):
        res = super(AccountInvoice, self).chorus_invoiceformat2syntax()
        res['xml_ubl'] = 'IN_DP_E1_UBL_INVOICE'
        return res

    def prepare_chorus_deposer_flux_payload(self):
        if self.company_id.fr_chorus_invoice_format == 'xml_ubl':
            xml_string = self.generate_ubl_xml_string()
            # Seems they don't want '/' in filenames
            filename =\
                'UBL_chorus_facture_%s.xml' % self.number.replace('/', '-')
            syntaxe_flux = self.chorus_invoiceformat2syntax()['xml_ubl']
            payload = {
                'fichierFlux': xml_string.encode('base64'),
                'nomFichier': filename,
                'syntaxeFlux': syntaxe_flux,
                'avecSignature': False,
                }
            return payload
        return super(
            AccountInvoice, self).prepare_chorus_deposer_flux_payload()
