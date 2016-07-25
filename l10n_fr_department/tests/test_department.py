# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.tests.common import TransactionCase


class TestFrDepartment(TransactionCase):

    def test_fr_department(self):
        rpo = self.env['res.partner']
        partner1 = rpo.create({
            'name': u'Akretion France',
            'street': u'35B rue Montgolfier',
            'zip': '69100',
            'city': u'Villeurbanne',
            'country_id': self.env.ref('base.fr').id,
        })
        self.assertEquals(
            partner1.department_id,
            self.env.ref('l10n_fr_department.res_country_department_rhone'))
        partner2 = rpo.create({
            'name': u'Abbaye du Barroux',
            'street': u'1201 chemin des Rabassières',
            'zip': '84330',
            'city': u'Le Barroux',
            'country_id': self.env.ref('base.fr').id,
        })
        self.assertEquals(
            partner2.department_id,
            self.env.ref('l10n_fr_department.res_country_department_vaucluse'))
