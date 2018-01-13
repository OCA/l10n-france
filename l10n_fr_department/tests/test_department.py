# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
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
