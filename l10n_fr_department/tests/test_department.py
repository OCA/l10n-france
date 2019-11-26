# Copyright 2016-2018 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestFrDepartment(TransactionCase):

    def test_fr_department(self):
        rpo = self.env['res.partner']
        partner1 = rpo.create({
            'name': 'Akretion France',
            'street': '35B rue Montgolfier',
            'zip': '69100',
            'city': 'Villeurbanne',
            'country_id': self.env.ref('base.fr').id,
        })
        self.assertEqual(
            partner1.department_id,
            self.env.ref('l10n_fr_department.res_country_department_rhone'))
        partner2 = rpo.create({
            'name': 'Abbaye du Barroux',
            'street': '1201 chemin des Rabassières',
            'zip': '84330',
            'city': 'Le Barroux',
            'country_id': self.env.ref('base.fr').id,
        })
        self.assertEqual(
            partner2.department_id,
            self.env.ref('l10n_fr_department.res_country_department_vaucluse'))

    def test_corse(self):
        rpo = self.env['res.partner']
        corse2A = self.env.ref(
            'l10n_fr_department.res_country_department_corsedusud'
        )
        corse2B = self.env.ref(
            'l10n_fr_department.res_country_department_hautecorse'
        )
        partner = rpo.create({
            'name': 'name',
            'street': 'street',
            'zip': '20000',
            'city': 'Ajaccio',
            'country_id': self.env.ref('base.fr').id,
        })
        self.assertEqual(partner.department_id, corse2A)

        partner.write({'zip': '20200', 'city': 'Bastia'})
        self.assertEqual(partner.department_id, corse2B)

        partner.write({'zip': '20190', 'city': 'Zigliara'})
        self.assertEqual(partner.department_id, corse2A)
        partner.write({'zip': '20620', 'city': 'Biguglia'})
        self.assertEqual(partner.department_id, corse2B)
        partner.write({'zip': '20999', 'city': 'Unknown'})
        self.assertFalse(partner.department_id)
