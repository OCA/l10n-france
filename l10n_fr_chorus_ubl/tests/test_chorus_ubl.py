# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestUblInvoice(TransactionCase):

    def test_chorus_ubl(self):
        aio = self.env['account.invoice']
        ailo = self.env['account.invoice.line']
        product = self.env.ref('product.product_product_4')
        uom = self.env.ref('product.product_uom_unit')
        company = self.env.ref('base.main_company')
        agreement = self.env.ref('l10n_fr_chorus_account.market3')
        partner = self.env.ref(
            'l10n_fr_chorus_account.national_education_ministry_service1')
        product_change = ailo.browse(False).product_id_change(
            product.id, uom.id, qty=1, partner_id=partner.id,
            currency_id=company.currency_id.id, company_id=company.id)
        partner_change = aio.browse(False).onchange_partner_id(
            'out_invoice', partner.id, company_id=company.id)
        vals = dict(
            partner_change['value'], partner_id=partner.id, name='EJ1242',
            agreement_id=agreement.id)
        il_vals = dict(product_change['value'], product_id=product.id)
        if il_vals['invoice_line_tax_id']:
            il_vals['invoice_line_tax_id'] = [
                (6, 0, il_vals['invoice_line_tax_id'])]
        vals['invoice_line'] = [(0, 0, il_vals)]
        invoice = aio.create(vals)
        invoice.action_invoice_open()
        action = invoice.attach_ubl_xml_file_button()
        self.assertEqual(action['res_model'], 'ir.attachment')
        attach = self.env['ir.attachment'].browse(action['res_id'])
        self.assertEqual(attach.datas_fname[-4:], '.xml')
