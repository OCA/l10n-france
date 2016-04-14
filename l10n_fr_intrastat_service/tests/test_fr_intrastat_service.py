# -*- coding: utf-8 -*-
# © 2016 Akretion (http://www.akretion.com/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# @author: Alexis de Lattre <alexis.delattre@akretion.com>

from openerp.tests.common import TransactionCase


class TestFrIntrastatService(TransactionCase):

    def test_generate_des(self):
        # Set company country to France
        company = self.env.ref('base.main_company')
        company.country_id = self.env.ref('base.fr')
        des = self.env['l10n.fr.intrastat.service.declaration'].create({
            'company_id': company.id})
        # We use the demo invoice provided by this module
        des.generate_service_lines()
        self.assertGreaterEqual(des.total_amount, 450)
        self.assertGreaterEqual(des.num_decl_lines, 1)
        des.done()
        self.assertEquals(des.state, 'done')
        des.generate_xml()
