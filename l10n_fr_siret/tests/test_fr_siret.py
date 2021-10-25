# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestL10nFrSiret(TransactionCase):
    def setUp(self):
        super().setUp()

    def test_siret(self):
        partner1 = self.env["res.partner"].create(
            {
                "name": "Akretion France",
                "siren": "792377731",
                "nic": "00023",
            }
        )
        self.assertEqual(partner1.siret, "79237773100023")
        # Try to update SIRET
        partner1.write({"siret": "81862078300048"})
        partner1.write({"siren": "792377731", "nic": "00023"})
        partner2 = self.env["res.partner"].create(
            {
                "name": "Akretion FR",
                "siret": "79237773100023",
            }
        )
        self.assertEqual(partner2.siren, "792377731")
        self.assertEqual(partner2.nic, "00023")
        self.assertTrue(partner2.same_siren_partner_id)
        partner3 = self.env["res.partner"].create(
            {
                "name": "Akretion FR SIREN only",
                "siren": "792377731",
            }
        )
        self.assertEqual(partner3.siret, "792377731*****")
        partner4 = self.env["res.partner"].create(
            {
                "name": "Akretion FR SIREN only",
                "siret": "792377731*****",
            }
        )
        self.assertEqual(partner4.siren, "792377731")
        self.assertFalse(partner4.nic)
        self.assertEqual(partner4.siret, "792377731*****")

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
