# -*- coding: utf-8 -*-
# Copyright 2017-2018 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


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
        if self.company_id.fr_chorus_invoice_format == 'xml_cii':
            xml_string = self.generate_facturx_xml()[0]
            # Seems they don't want '/' in filenames
            filename =\
                'CII_16B_chorus_facture_%s.xml' % self.number.replace('/', '-')
            syntaxe_flux = self.chorus_invoiceformat2syntax()['xml_cii']
            payload = {
                'fichierFlux': xml_string.encode('base64'),
                'nomFichier': filename,
                'syntaxeFlux': syntaxe_flux,
                'avecSignature': False,
                }
            return payload
        return super(
            AccountInvoice, self).prepare_chorus_deposer_flux_payload()
