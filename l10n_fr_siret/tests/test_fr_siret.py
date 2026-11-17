# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestL10nFrSiret(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company1_id = self.env.ref("base.main_company").id
        partner_company = self.env["res.partner"].create(
            {
                "name": "Test Company",
                "is_company": True,
                "country_id": self.env.ref("base.fr").id,
            }
        )
        self.company2_id = (
            self.env["res.company"]
            .create(
                {
                    "name": "Test Company",
                    "partner_id": partner_company.id,
                    "currency_id": self.env.ref("base.EUR").id,
                }
            )
            .id
        )

    def test_siret(self):
        partner1 = self.env["res.partner"].create(
            {
                "name": "Test partner1",
                "siren": "555555556",
                "nic": "00011",
            }
        )
        self.assertEqual(partner1.siret, "55555555600011")
        self.assertFalse(partner1.same_siren_partner_id)
        # Try to update SIRET
        partner1.write({"siret": "81862078300048"})
        partner1.write({"siren": "792377731", "nic": "00023"})
        partner1.write({"siret": "55555555600011"})
        partner2 = self.env["res.partner"].create(
            {
                "name": "Test partner2",
                "siret": "55555555600011",
            }
        )
        self.assertEqual(partner2.siren, "555555556")
        self.assertEqual(partner2.nic, "00011")
        self.assertEqual(partner2.same_siren_partner_id, partner1)
        self.assertEqual(partner1.same_siren_partner_id, partner2)
        partner3 = self.env["res.partner"].create(
            {
                "name": "Test SIREN only",
                "siren": "555555556",
            }
        )
        self.assertEqual(partner3.siret, "555555556*****")
        partner4 = self.env["res.partner"].create(
            {
                "name": "Test SIREN only",
                "siret": "555555556*****",
            }
        )
        self.assertEqual(partner4.siren, "555555556")
        self.assertFalse(partner4.nic)
        self.assertEqual(partner4.siret, "555555556*****")

    def test_wrong_siret(self):
        vals = {"name": "Wrong Akretion France"}
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(dict(vals, siret="79237773100022"))

        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(dict(vals, siret="792377731"))

        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(dict(vals, siret="78237773100023"))

        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(dict(vals, siren="782377731", nic="00023"))

        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(dict(vals, siren="792377731", nic="00022"))

    def test_warn_banner_multi_company(self):
        partner_company1 = self.env["res.partner"].create(
            {
                "name": "TestDup",
                "siren": "444444442",
                "company_id": self.company1_id,
            }
        )
        partner_company2 = self.env["res.partner"].create(
            {
                "name": "TestDup",
                "siren": "444444442",
                "nic": "00016",
                "company_id": self.company2_id,
            }
        )
        self.assertFalse(partner_company1.same_siren_partner_id)
        self.assertFalse(partner_company2.same_siren_partner_id)
        partner_company2.write({"company_id": False})
        self.assertEqual(partner_company2.same_siren_partner_id, partner_company1)

    def test_change_parent_id(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Akretion France",
                "siren": "792377731",
                "nic": "00023",
            }
        )

        partner2 = self.env["res.partner"].create(
            {
                "name": "Akretion Fr",
                "siren": "784671695",
                "nic": "00087",
            }
        )

        contact = self.env["res.partner"].create(
            {"name": "Test contact", "parent_id": partner.id}
        )

        self.assertEqual(partner.siren, contact.siren)
        self.assertEqual(partner.nic, contact.nic)

        contact.write({"parent_id": partner2.id})

        self.assertEqual(partner2.siren, contact.siren)
        self.assertEqual(partner2.nic, contact.nic)

    def test_vat_siren_consistency(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Test partner1",
                    "country_id": self.env.ref("base.fr").id,
                    "siren": "790067136",
                    "vat": "FR86792377731",
                }
            )
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create(
                {
                    "name": "Test partner1",
                    "country_id": self.env.ref("base.fr").id,
                    "siret": "79006713600016",
                    "vat": "FR86792377731",
                }
            )
        self.env["res.partner"].create(
            {
                "name": "Akretion France",
                "country_id": self.env.ref("base.fr").id,
                "siren": "792377731",
                "vat": "FR86792377731",
            }
        )

    def test_get_methods(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Akretion France",
                "is_company": True,
                "country_id": self.env.ref("base.fr").id,
                "siren": "792377731",
                "nic": "00023",
            }
        )
        self.assertTrue(partner.is_france_country)
        self.assertEqual(partner._get_siren(), "792377731")
        self.assertEqual(partner._get_siret(), "79237773100023")
        self.assertEqual(partner._get_nic(), "00023")
        contact = self.env["res.partner"].create(
            {"name": "Contact", "parent_id": partner.id}
        )
        self.assertEqual(contact._get_siren(), "792377731")
        vat_only = self.env["res.partner"].create(
            {"name": "VAT only", "vat": "FR86792377731"}
        )
        self.assertFalse(vat_only.is_france_country)
        self.assertEqual(vat_only._get_siren(), "792377731")
        empty = self.env["res.partner"].create({"name": "Empty"})
        self.assertIsNone(empty._get_siren())
        self.assertIsNone(empty._get_siret())
        self.assertIsNone(empty._get_nic())
        with self.assertRaises(UserError):
            empty._get_siren(raise_if_none=True)
        with self.assertRaises(UserError):
            empty._get_siret(raise_if_none=True)
        with self.assertRaises(UserError):
            empty._get_nic(raise_if_none=True)

    def test_company_is_france_country(self):
        company = self.env["res.company"].browse(self.company2_id)
        self.assertTrue(company.is_france_country)
        company.country_id = self.env.ref("base.be")
        self.assertFalse(company.is_france_country)
