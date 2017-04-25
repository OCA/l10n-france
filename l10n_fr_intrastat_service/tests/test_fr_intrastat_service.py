# -*- coding: utf-8 -*-
# © 2016-2017 Akretion (http://www.akretion.com/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# @author: Alexis de Lattre <alexis.delattre@akretion.com>

from odoo.tests.common import TransactionCase
from odoo.tools import float_compare
from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import etree


class TestFrIntrastatService(TransactionCase):

    def setUp(self):
        super(TestFrIntrastatService, self).setUp()
        # Set company country to France
        self.company = self.env.ref('base.main_company')
        self.company.country_id = self.env.ref('base.fr')
        self.invoice_model = self.env['account.invoice']
        self.invoice_line_model = self.env['account.invoice.line']
        self.account_account_model = self.env['account.account']
        self.account_receivable = self.account_account_model.search(
            [('code', '=', '411100')], limit=1)

        if not self.account_receivable:
            self.account_receivable = self.account_account_model.create({
                'code': '411100',
                'name': 'Debtors - (test)',
                'reconcile': True,
                'user_type_id':
                self.ref('account.data_account_type_receivable')
                })
        self.account_revenue = self.account_account_model.search(
            [('code', '=', '706000')], limit=1)
        if not self.account_revenue:
            self.account_revenue = self.account_account_model.create({
                'code': '706000',
                'name': 'Service Sales - (test)',
                'user_type_id':
                self.ref('account.data_account_type_revenue')
                })

        # create first invoice
        date = datetime.now() + relativedelta(day=5, months=-1)
        inv1 = self.invoice_model.create({
            'partner_id': self.env.ref('base.res_partner_2').id,
            'currency_id': self.env.ref('base.EUR').id,
            'account_id': self.account_receivable.id,
            'type': 'out_invoice',
            'date_invoice': date,
        })
        self.invoice_line_model.create({
            'product_id': self.env.ref('product.service_cost_01').id,
            'quantity': 5,
            'price_unit': 90,
            'invoice_id': inv1.id,
            'name': 'Audit service',
            'account_id': self.account_revenue.id,
        })
        self.invoice_line_model.create({
            'product_id': self.env.ref('product.product_product_25').id,
            'quantity': 1,
            'price_unit': 1950,
            'invoice_id': inv1.id,
            'name': 'Laptop',
            'account_id': self.account_revenue.id,
        })
        inv1.action_invoice_open()
        # create 2nd invoice
        inv2 = self.invoice_model.create({
            'partner_id': self.env.ref('base.res_partner_2').id,
            'currency_id': self.env.ref('base.EUR').id,
            'account_id': self.account_receivable.id,
            'type': 'out_invoice',
            'date_invoice': date,
        })
        self.invoice_line_model.create({
            'product_id': self.env.ref('product.product_product_1').id,
            'quantity': 2,
            'price_unit': 90.2,
            'invoice_id': inv2.id,
            'name': 'GAP Analysis for your Odoo v10 project',
            'account_id': self.account_revenue.id,
        })
        self.invoice_line_model.create({
            'product_id': self.env.ref('product.product_product_7').id,
            'quantity': 1,
            'price_unit': 45,
            'invoice_id': inv2.id,
            'name': 'Apple headphones',
            'account_id': self.account_revenue.id,
        })
        inv2.action_invoice_open()
        # create refund
        inv3 = self.invoice_model.create({
            'partner_id': self.env.ref('base.res_partner_2').id,
            'currency_id': self.env.ref('base.EUR').id,
            'account_id': self.account_receivable.id,
            'type': 'out_refund',
            'date_invoice': date,
        })
        self.invoice_line_model.create({
            'product_id': self.env.ref('product.service_order_01').id,
            'quantity': 1,
            'price_unit': 90,
            'invoice_id': inv3.id,
            'name': 'Refund consulting hour',
            'account_id': self.account_revenue.id,
        })
        inv3.action_invoice_open()

    def test_generate_des(self):
        des = self.env['l10n.fr.intrastat.service.declaration'].create({
            'company_id': self.company.id})
        des.generate_service_lines()
        self.assertEqual(float_compare(
            des.total_amount, 540.0, precision_digits=2), 0)
        self.assertEqual(des.num_decl_lines, 3)
        des.done()
        self.assertEquals(des.state, 'done')
        des.generate_xml()
        xml_des_files = self.env['ir.attachment'].search([
            ('res_id', '=', des.id),
            ('res_model', '=', 'l10n.fr.intrastat.service.declaration'),
            ('type', '=', 'binary'),
            ])
        self.assertEquals(len(xml_des_files), 1)
        xml_des_file = xml_des_files[0]
        self.assertEquals(xml_des_file.datas_fname[-4:], '.xml')
        xml_root = etree.fromstring(xml_des_file.datas.decode('base64'))
        company_vat_xpath = xml_root.xpath(
            '/fichier_des/declaration_des/num_tvaFr')
        self.assertEquals(company_vat_xpath[0].text, self.company.vat)
        lines_xpath = xml_root.xpath('/fichier_des/declaration_des/ligne_des')
        self.assertEquals(len(lines_xpath), des.num_decl_lines)
