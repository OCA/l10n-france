# -*- coding: utf-8 -*-
# © 2016 Akretion (http://www.akretion.com/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# @author: Alexis de Lattre <alexis.delattre@akretion.com>

from openerp.tests.common import TransactionCase
from openerp.tools import float_compare
from lxml import etree


class TestFrIntrastatService(TransactionCase):

    def test_generate_des(self):
        # Set company country to France
        company = self.env.ref('base.main_company')
        company.country_id = self.env.ref('base.fr')
        des = self.env['l10n.fr.intrastat.service.declaration'].create({
            'company_id': company.id})
        # We use the demo invoice provided by this module
        des.generate_service_lines()
        precision = self.env['decimal.precision'].precision_get('Account')
        self.assertEqual(float_compare(
            des.total_amount, 540.0, precision_digits=precision), 0)
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
        self.assertEquals(company_vat_xpath[0].text, company.vat)
        lines_xpath = xml_root.xpath('/fichier_des/declaration_des/ligne_des')
        self.assertEquals(len(lines_xpath), des.num_decl_lines)
