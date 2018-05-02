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

    def chorus_get_invoice(self, chorus_invoice_format):
        self.ensure_one()
        if chorus_invoice_format == 'xml_cii':
            # Our syntax doesn't comply to what Chorus expects for CII 16B
            chorus_file_content = self.generate_facturx_xml()[0]
        elif chorus_invoice_format == 'pdf_factur-x':
            # deposerFlux works in Factur-X for single invoice,
            # but not in multi-invoice with tarball
            chorus_file_content = self.env['report'].get_pdf(
                self.ids, 'account.report_invoice')
        else:
            chorus_file_content = super(AccountInvoice, self).\
                chorus_get_invoice(chorus_invoice_format)
        return chorus_file_content
