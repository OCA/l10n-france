# Copyright 2024 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestFrDas2(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env["res.company"].create(
            {
                "name": "Test company DAS2",
                "street": "42, rue de la paix",
                "zip": "69100",
                "city": "Villeurbanne",
                "country_id": cls.env.ref("base.fr").id,
                "currency_id": cls.env.ref("base.EUR").id,
                "siren": "792377731",
                "nic": "00023",
                "ape": "6202Z",
            }
        )
        cls.env.user.phone = "+33742124212"
        cls.partner1 = cls.env["res.partner"].create(
            {
                "is_company": True,
                "name": "Mon expert comptable préféré",
                "street": "42 rue du chiffre",
                "zip": "69009",
                "city": "Lyon",
                "country_id": cls.env.ref("base.fr").id,
                "email": "experts@comptables.example.com",
                "fr_das2_type": "fee",
                "fr_das2_job": "Expert comptable",
                "siren": "555555556",
                "nic": "00011",
            }
        )
        cls.partner2 = cls.env["res.partner"].create(
            {
                "is_company": True,
                "name": "Mon avocat",
                "street": "12 rue du tribunal",
                "zip": "69009",
                "city": "Lyon",
                "country_id": cls.env.ref("base.fr").id,
                "email": "avocat@example.com",
                "fr_das2_type": "fee",
                "fr_das2_job": "Avocat",
                "siren": "666666664",
                "nic": "00014",
            }
        )

    def test_das2(self):
        decl = self.env["l10n.fr.das2"].create(
            {
                "year": 2023,
                "company_id": self.company.id,
                "payment_journal_ids": [],
            }
        )
        self.assertEqual(self.partner1.siret, "55555555600011")
        self.env["l10n.fr.das2.line"].create(
            {
                "partner_id": self.partner1.id,
                "parent_id": decl.id,
                "fee_amount": 2000,
            }
        )
        self.env["l10n.fr.das2.line"].create(
            {
                "partner_id": self.partner2.id,
                "parent_id": decl.id,
                "fee_amount": 3123,
            }
        )
        self.assertEqual(decl.state, "draft")
        decl.done()
        self.assertEqual(decl.state, "done")
        self.assertTrue(decl.attachment_id)
        self.assertTrue(
            decl.attachment_id.name.startswith(
                f"DSAL_{decl.year}_{decl.company_id.siren}_000_"
            )
        )
        self.assertTrue(decl.attachment_id.name.endswith(".txt.gz.gpg"))
        self.assertTrue(decl.unencrypted_attachment_id)
        self.assertTrue(decl.unencrypted_attachment_id.name.endswith(".txt"))
