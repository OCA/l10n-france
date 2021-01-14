# Copyright 2016-2018 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields
from odoo.tests import SavepointCase


class TestPurchaseEcotaxe(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestPurchaseEcotaxe, cls).setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test"})
        cls.purchase = cls.env["purchase.order"].create(
            {
                "name": "Test Customer purchase",
                "partner_id": cls.partner.id,
            }
        )
        cls.product = cls.env["product.template"].create(
            {
                "name": "Product Test",
                "list_price": 100.00,
                "weight": 100.00,
            }
        )

        cls.purchase_line = cls.env["purchase.order.line"]
        cls.purchase_line1 = cls.purchase_line.create(
            {
                "order_id": cls.purchase.id,
                "name": "Line 1",
                "price_unit": 100,
                "product_id": cls.product.product_variant_ids[:1].id,
                "product_qty": 1,
                "date_planned": fields.Datetime.now(),
                "product_uom": cls.product.uom_id.id,
            }
        )
        cls.ecotaxe_classification = cls.env["account.ecotaxe.classification"]
        cls.ecotaxe_classification1 = cls.ecotaxe_classification.create(
            {
                "name": "Fixed Ecotaxe",
                "ecotaxe_type": "fixed",
                "default_fixed_ecotaxe": 2.4,
                "ecotaxe_product_status": "M",
                "ecotaxe_supplier_status": "FAB",
            }
        )
        cls.ecotaxe_classification2 = cls.ecotaxe_classification.create(
            {
                "name": "Weight based",
                "ecotaxe_type": "weight_based",
                "ecotaxe_coef": 0.04,
                "ecotaxe_product_status": "P",
                "ecotaxe_supplier_status": "FAB",
            }
        )
        cls.product2 = cls.env["product.template"].create(
            {
                "name": "Product Test 2",
                "list_price": 2000.00,
                "weight": 400.00,
                "ecotaxe_classification_id": cls.ecotaxe_classification2.id,
                "sale_line_warn": "no-message",
            }
        )

    def test_01_manual_fixed_ecotaxe(self):
        """ Tests multiple lines with fixed ecotaxes """
        self.product.manual_fixed_ecotaxe = 1.5
        self.product._compute_ecotaxe()
        self.assertEqual(self.product.ecotaxe_amount, 1.5)
        self.purchase_line1.product_qty = 4
        self.assertEqual(self.purchase_line1.unit_ecotaxe_amount, 1.5)
        self.assertEqual(self.purchase_line1.subtotal_ecotaxe, 6.0)
        self.assertEqual(self.purchase.amount_total, 400.0)
        self.assertEqual(self.purchase.amount_ecotaxe, 6.0)

    def test_02_classification_weight_based_ecotaxe(self):
        """ Tests multiple lines with weight based ecotaxes """
        self.product.ecotaxe_classification_id = self.ecotaxe_classification2
        self.product._compute_ecotaxe()
        self.assertEqual(self.product.ecotaxe_amount, 4)
        self.purchase_line1.product_qty = 3
        self.assertEqual(self.purchase_line1.unit_ecotaxe_amount, 4)
        self.assertEqual(self.purchase_line1.subtotal_ecotaxe, 12)
        self.assertEqual(self.purchase.amount_total, 300.0)
        self.assertEqual(self.purchase.amount_ecotaxe, 12)

    def test_03_classification_ecotaxe(self):
        """ Tests multiple lines with mixed ecotaxes """
        self.product.ecotaxe_classification_id = self.ecotaxe_classification1
        self.product._compute_ecotaxe()
        self.assertEqual(self.product.ecotaxe_amount, 2.4)
        self.purchase_line1.product_qty = 3
        self.purchase_line2 = self.purchase_line.create(
            {
                "order_id": self.purchase.id,
                "name": "Line 1",
                "price_unit": 2000,
                "product_id": self.product2.product_variant_ids[:1].id,
                "product_qty": 2,
                "date_planned": fields.Datetime.now(),
                "product_uom": self.product2.uom_id.id,
            }
        )
        self.assertEqual(self.purchase_line1.unit_ecotaxe_amount, 2.4)
        self.assertEqual(self.purchase_line1.subtotal_ecotaxe, 7.2)
        self.assertEqual(self.purchase_line2.unit_ecotaxe_amount, 16)
        self.assertEqual(self.purchase_line2.subtotal_ecotaxe, 32)
        self.assertEqual(self.purchase.amount_total, 4300.0)
        self.assertEqual(self.purchase.amount_ecotaxe, 39.2)
