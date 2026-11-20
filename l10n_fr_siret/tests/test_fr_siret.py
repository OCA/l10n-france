# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestL10nFrSiret(TransactionCase):
    _test_user_groups = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company1_id = cls.env.ref("base.main_company").id
        cls.company2_id = (
            cls.env["res.company"]
            .create(
                {
                    "name": "Test Company",
                    "currency_id": cls.env.ref("base.EUR").id,
                }
            )
            .id
        )
        cls.valid_siren = "792 377 731"
        cls.valid_siren_no_space = "792377731"
        cls.valid_siret = f"{cls.valid_siren} 00023"
        cls.valid_siret_no_space = f"{cls.valid_siren_no_space}00023"
        cls.valid_vat = "FR 86 792377731"
        cls.valid_siren2 = "987 654 324"
        cls.valid_siret2 = f"{cls.valid_siren2} 00019"

    def test_siret(self):
        partner1 = self.env["res.partner"].create(
            {
                "name": "Test partner1",
                "country_id": self.env.ref("base.fr").id,
                "additional_identifiers": {"FR_SIRET": "55555555600011"},
            }
        )
        self.assertEqual(partner1._get_siret(), "55555555600011")
        self.assertEqual(partner1._get_siren(), "555555556")
        partner1.write({"country_id": self.env.ref("base.ag").id})
        self.assertFalse(partner1._get_siret())
        self.assertFalse(partner1._get_siren())
        with self.assertRaises(UserError):
            self.assertFalse(partner1._get_siret(raise_if_none=True))
        with self.assertRaises(UserError):
            self.assertFalse(partner1._get_siren(raise_if_none=True))
        partner1.write({"country_id": self.env.ref("base.fr").id})
        self.assertFalse(partner1.same_siren_partner_ids)
        # Try to update SIRET
        partner1.write({"country_id": self.env.ref("base.fr").id})
        partner1.write({"additional_identifiers": {"FR_SIRET": "81862078300048"}})
        partner1.write({"additional_identifiers": {"FR_SIRET": "79237773100023"}})
        partner1.write({"additional_identifiers": {"FR_SIRET": "55555555600011"}})

        partner2 = self.env["res.partner"].create(
            {
                "name": "Test partner2",
                "country_id": self.env.ref("base.fr").id,
                "additional_identifiers": {"FR_SIRET": "55555555600011"},
            }
        )
        self.assertEqual(partner2._get_siren(), "555555556")
        self.assertEqual(partner2._get_nic(), "00011")
        self.assertEqual(partner2.same_siren_partner_ids, partner1)
        self.assertEqual(partner1.same_siren_partner_ids, partner2)
        partner3 = self.env["res.partner"].create(
            {
                "name": "Test SIREN only",
                "additional_identifiers": {"FR_SIREN": "555555556"},
                "country_id": self.env.ref("base.fr").id,
            }
        )
        self.assertEqual(partner3._get_siren(), "555555556")
        self.assertFalse(partner3._get_nic())
        self.assertIn(partner1, partner3.same_siren_partner_ids)
        self.assertIn(partner2, partner3.same_siren_partner_ids)

    def test_company(self):
        vals = {
            "name": "New company",
            "country_id": self.env.ref("base.fr").id,
        }
        c1 = self.env["res.company"].create(
            dict(
                vals,
                additional_identifiers={"FR_SIRET": self.valid_siret},
                vat=self.valid_vat,
            )
        )
        self.assertEqual(c1._get_siret(), self.valid_siret.replace(" ", ""))
        self.assertEqual(c1._get_siren(), self.valid_siren.replace(" ", ""))
        self.assertEqual(c1._get_nic(), "00023")

    def test_warn_banner_multi_company(self):
        partner_company1 = self.env["res.partner"].create(
            {
                "name": "TestDup",
                "additional_identifiers": {"FR_SIREN": "444444442"},
                "company_id": self.company1_id,
                "country_id": self.env.ref("base.fr").id,
            }
        )
        partner_company2 = self.env["res.partner"].create(
            {
                "name": "TestDup",
                "additional_identifiers": {"FR_SIRET": "44444444200016"},
                "company_id": self.company2_id,
                "country_id": self.env.ref("base.fr").id,
            }
        )
        self.assertFalse(partner_company1.same_siren_partner_ids)
        self.assertFalse(partner_company2.same_siren_partner_ids)
        partner_company2.write({"company_id": False})
        self.assertEqual(partner_company2.same_siren_partner_ids, partner_company1)

    def test_change_parent_id(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Akretion France",
                "country_id": self.env.ref("base.fr").id,
                "additional_identifiers": {"FR_SIRET": "79237773100023"},
            }
        )
        partner2 = self.env["res.partner"].create(
            {
                "name": "Akretion Fr",
                "country_id": self.env.ref("base.fr").id,
                "additional_identifiers": {"FR_SIRET": "78467169500087"},
            }
        )
        contact = self.env["res.partner"].create(
            {"name": "Test contact", "parent_id": partner.id}
        )

        self.assertEqual(partner._get_siren(), contact._get_siren())
        self.assertEqual(partner._get_siret(), contact._get_siret())
        self.assertEqual(partner._get_nic(), contact._get_nic())

        contact.write({"parent_id": partner2.id})

        self.assertEqual(partner2._get_siren(), contact._get_siren())
        self.assertEqual(partner2._get_siret(), contact._get_siret())
        self.assertEqual(partner2._get_nic(), contact._get_nic())

    def test_parent_child_siren_consistency(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Akretion France",
                "country_id": self.env.ref("base.fr").id,
                "additional_identifiers": {"FR_SIRET": "79237773100023"},
            }
        )

        # Create
        with self.assertRaises(ValidationError):
            child_partner = self.env["res.partner"].create(
                {
                    "name": "Invoicing child partner",
                    "parent_id": partner.id,
                    "country_id": self.env.ref("base.fr").id,
                    "type": "invoice",
                    "additional_identifiers": {"FR_SIRET": "11998877200024"},
                }
            )

        # Write on child
        child_partner = self.env["res.partner"].create(
            {
                "name": "Invoicing child partner",
                "parent_id": partner.id,
                "country_id": self.env.ref("base.fr").id,
                "type": "invoice",
                "additional_identifiers": {"FR_SIRET": "79237773100023"},
            }
        )
        with self.assertRaises(ValidationError):
            child_partner.additional_identifiers = {"FR_SIRET": "33998877600029"}

        # Write on parent
        partner.additional_identifiers = {"FR_SIREN": "792377731", "FR_SIRET": False}
        self.assertEqual(child_partner._get_siren(), partner._get_siren())

        # also test when creating parent and child at the same time
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Test me",
                    "country_id": self.env.ref("base.fr").id,
                    "additional_identifiers": {"FR_SIRET": "22998877900026"},
                    "child_ids": [
                        Command.create(
                            {
                                "name": "Child test",
                                "country_id": self.env.ref("base.fr").id,
                                "type": "invoice",
                                "additional_identifiers": {
                                    "FR_SIRET": "33998877600029"
                                },
                            }
                        )
                    ],
                }
            )
