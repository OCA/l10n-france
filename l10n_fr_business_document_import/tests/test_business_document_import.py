# Copyright 2016-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestL10nFRBusinessDocumentImport(TransactionCase):
    def test_match_partner_siren_siret(self):
        partner1 = self.env["res.partner"].create(
            {
                "name": "France Telecom (siège)",
                "supplier_rank": 1,
                "is_company": True,
                "siren": "380129866",
                "nic": "46850",
            }
        )
        partner2 = self.env["res.partner"].create(
            {
                "name": "France Telecom Lyon",
                "supplier_rank": 1,
                "is_company": True,
                "siren": "380129866",
                "nic": "00014",
            }
        )
        bdio = self.env["business.document.import"]
        partner_dict = {"siren": "380 129 866"}
        res = bdio._match_partner(partner_dict, [])
        self.assertIn(res, [partner1, partner2])
        partner_dict = {"siret": "380 129 866 46850"}
        res = bdio._match_partner(partner_dict, [])
        self.assertEqual(res, partner1)
        partner_dict = {"siret": "380 129 866 00022"}
        res = bdio._match_partner(partner_dict, [])
        self.assertIn(res, [partner1, partner2])
        partner3 = self.env["res.partner"].create(
            {
                "name": "Renault",
                "is_company": True,
                "vat": "FR63441639465",
                "country_id": self.env.ref("base.fr").id,
            }
        )
        partner_dict = {"siren": "441639465"}
        self.assertEqual(bdio._match_partner(partner_dict, []), partner3)
