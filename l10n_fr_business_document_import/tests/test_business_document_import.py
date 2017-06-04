# -*- coding: utf-8 -*-
# © 2016-2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestL10nFRBusinessDocumentImport(TransactionCase):

    def test_match_partner_siren(self):
        partner1 = self.env['res.partner'].create({
            'name': 'France Telecom',
            'supplier': True,
            'is_company': True,
            'siren': '380129866',
            })
        bdio = self.env['business.document.import']
        partner_dict = {'siren': '380 129 866'}
        res = bdio._match_partner(partner_dict, [])
        self.assertEquals(res, partner1)
