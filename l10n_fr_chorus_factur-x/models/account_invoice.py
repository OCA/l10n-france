# -*- coding: utf-8 -*-
# Copyright 2017-2018 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _cii_trade_contact_department_name(self, partner):
        if partner.fr_chorus_service_code:
            return partner.name
        return super(AccountInvoice, self)._cii_trade_contact_department_name(
            partner)

    @api.model
    def _cii_trade_agreement_buyer_ref(self, partner):
        if partner.fr_chorus_service_code:
            return partner.fr_chorus_service_code
        return super(AccountInvoice, self)._cii_trade_contact_department_name(
            partner)

    def prepare_chorus_deposer_flux_payload(self):
        chorus_format = self.company_id.fr_chorus_invoice_format
        cfo = self.env['chorus.flow']
        if chorus_format in ['xml_cii', 'pdf_factur-x']:
            syntaxe_flux = cfo.syntax_odoo2chorus()[chorus_format]
            if len(self) == 1:
                # Seems they don't want '/' in filenames
                inv_ref = self.number.replace('/', '-')
                if chorus_format == 'xml_cii':
                    chorus_file_content = self.generate_facturx_xml()[0]
                    filename = 'CII_16B_chorus_facture_%s.xml' % inv_ref
                elif chorus_format == 'pdf_factur-x':
                    filename = 'FacturX_chorus_%s.pdf' % inv_ref
                    chorus_file_content = self.env['report'].get_pdf(
                        self.ids, 'account.report_invoice')
            else:
                raise UserError(
                    'TODO: add support for sending multiple invoices '
                    'at the same time.')
            payload = {
                'fichierFlux': chorus_file_content.encode('base64'),
                'nomFichier': filename,
                'syntaxeFlux': syntaxe_flux,
                'avecSignature': False,
                }
            return payload
        return super(
            AccountInvoice, self).prepare_chorus_deposer_flux_payload()
