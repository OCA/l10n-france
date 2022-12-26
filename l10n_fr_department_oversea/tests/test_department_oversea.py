# Copyright 2016-2022 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase


class TestFrDepartmentOversea(TransactionCase):
    def test_fr_department_oversea(self):
        rpo = self.env["res.partner"]
        partner1 = rpo.create(
            {
                "name": "Monsieur Payet",
                "street": "11 rue du Stade",
                "street2": "Montgaillard",
                "zip": "97400",
                "city": "Saint Denis",
                "country_id": self.env.ref("base.re").id,
            }
        )
        self.assertEqual(
            partner1.country_department_id,
            self.env.ref("l10n_fr_department_oversea.res_country_department_reunion"),
        )
        # I also want it to work if you select France as country
        partner2 = rpo.create(
            {
                "name": "Monsieur Hoarau",
                "street": "13 rue du Stade",
                "street2": "Montgaillard",
                "zip": "97400",
                "city": "Saint Denis",
                "country_id": self.env.ref("base.fr").id,
            }
        )
        self.assertEqual(
            partner2.country_department_id,
            self.env.ref("l10n_fr_department_oversea.res_country_department_reunion"),
        )
