# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestFrDepartmentOversea(TransactionCase):

    def test_fr_department_oversea(self):
        rpo = self.env['res.partner']
        partner1 = rpo.create({
            'name': u'Monsieur Payet',
            'street': u'11 rue du Stade',
            'street2': u'Montgaillard',
            'zip': '97400',
            'city': u'Saint Denis',
            'country_id': self.env.ref('base.re').id,
        })
        self.assertEquals(
            partner1.department_id,
            self.env.ref(
                'l10n_fr_department_oversea.res_country_department_reunion'))
        # I also want it to work if you select France as country
        partner2 = rpo.create({
            'name': u'Monsieur Hoarau',
            'street': u'13 rue du Stade',
            'street2': u'Montgaillard',
            'zip': '97400',
            'city': u'Saint Denis',
            'country_id': self.env.ref('base.fr').id,
        })
        self.assertEquals(
            partner2.department_id,
            self.env.ref(
                'l10n_fr_department_oversea.res_country_department_reunion'))
