# -*- coding: utf-8 -*-
# Copyright 2017-2018 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _cii_trade_contact_department_name(self, partner):
        if partner.fr_chorus_service_id:
            return partner.name
        return super(AccountInvoice, self)._cii_trade_contact_department_name(
            partner)

    @api.model
    def _cii_trade_agreement_buyer_ref(self, partner):
        if partner.fr_chorus_service_id:
            return partner.fr_chorus_service_id.code
        return super(AccountInvoice, self)._cii_trade_agreement_buyer_ref(
            partner)

    def chorus_get_invoice(self, chorus_invoice_format):
        self.ensure_one()
        if chorus_invoice_format == 'xml_cii':
            chorus_file_content = self.with_context(
                fr_chorus_cii16b=True).generate_facturx_xml()[0]
        elif chorus_invoice_format == 'pdf_factur-x':
            chorus_file_content, filetype = self.env['ir.actions.report.xml'].\
                render_report(self.ids, 'account.report_invoice', {})
            assert filetype == 'pdf', 'wrong filetype'
        else:
            chorus_file_content = super(AccountInvoice, self).\
                chorus_get_invoice(chorus_invoice_format)
        return chorus_file_content
