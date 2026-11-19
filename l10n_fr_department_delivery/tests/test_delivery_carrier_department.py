# Copyright (C) 2026 Akretion (<http://www.akretion.com>).
# @author Kévin Roche <kevin.roche@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.addons.base.tests.common import BaseCommon


class TestDeliveryCarrierDepartment(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        france = cls.env.ref("base.fr")
        department_model = cls.env["res.country.department"]
        cls.dep_69 = department_model.search(
            [("code", "=", "69"), ("country_id", "=", france.id)], limit=1
        )
        cls.dep_75 = department_model.search(
            [("code", "=", "75"), ("country_id", "=", france.id)], limit=1
        )
        product = cls.env["product.product"].create(
            {"name": "Test Delivery Product", "type": "service"}
        )
        cls.carrier = cls.env["delivery.carrier"].create(
            {
                "name": "Test Carrier",
                "product_id": product.id,
                "delivery_type": "fixed",
            }
        )
        partner_model = cls.env["res.partner"]
        cls.partner_lyon = partner_model.create(
            {"name": "Partner Lyon", "country_id": france.id, "zip": "69001"}
        )
        cls.partner_paris = partner_model.create(
            {"name": "Partner Paris", "country_id": france.id, "zip": "75001"}
        )
        cls.partner_no_department = partner_model.create(
            {"name": "Partner No Department", "country_id": france.id}
        )

    def test_no_restriction(self):
        self.assertTrue(self.carrier._match_address(self.partner_lyon))
        self.assertTrue(self.carrier._match_address(self.partner_paris))
        self.assertTrue(self.carrier._match_address(self.partner_no_department))

    def test_allowed_departments(self):
        self.carrier.department_ids = self.dep_69
        self.assertTrue(self.carrier._match_address(self.partner_lyon))
        self.assertFalse(self.carrier._match_address(self.partner_paris))
        self.assertFalse(self.carrier._match_address(self.partner_no_department))

    def test_unallowed_departments(self):
        self.carrier.unallowed_department_ids = self.dep_69
        self.assertFalse(self.carrier._match_address(self.partner_lyon))
        self.assertTrue(self.carrier._match_address(self.partner_paris))
        self.assertTrue(self.carrier._match_address(self.partner_no_department))

    def test_allowed_and_unallowed_departments(self):
        self.carrier.department_ids = self.dep_69 | self.dep_75
        self.carrier.unallowed_department_ids = self.dep_75
        self.assertTrue(self.carrier._match_address(self.partner_lyon))
        self.assertFalse(self.carrier._match_address(self.partner_paris))

    def test_country_restriction_still_applies(self):
        self.carrier.country_ids = self.env.ref("base.be")
        self.carrier.unallowed_department_ids = self.dep_75
        self.assertFalse(self.carrier._match_address(self.partner_lyon))
