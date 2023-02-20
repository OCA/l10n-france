# Copyright 2016-2018 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import SavepointCase


class TestInvoiceEcotaxe(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestInvoiceEcotaxe, cls).setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test"})
        cls.account_type = cls.env["account.account.type"].create(
            {
                "name": "Test",
                "type": "receivable",
            }
        )
        cls.account = cls.env["account.account"].create(
            {
                "name": "Test account",
                "code": "TEST",
                "user_type_id": cls.account_type.id,
                "reconcile": True,
            }
        )
        cls.invoice = cls.env["account.invoice"].create(
            {
                "name": "Test Customer Invoice",
                "journal_id": cls.env["account.journal"]
                .search([("type", "=", "sale")])[0]
                .id,
                "partner_id": cls.partner.id,
                "account_id": cls.account.id,
            }
        )
        cls.product = cls.env["product.template"].create(
            {
                "name": "Product Test",
                "list_price": 100.00,
                "weight": 100.00,
            }
        )

        cls.invoice_line = cls.env["account.invoice.line"]
        cls.invoice_line1 = cls.invoice_line.create(
            {
                "invoice_id": cls.invoice.id,
                "name": "Line 1",
                "price_unit": 100,
                "product_id": cls.product.product_variant_ids[:1].id,
                "account_id": cls.account.id,
                "quantity": 1,
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
            }
        )

    def test_01_manual_fixed_ecotaxe(self):
        """ Tests multiple lines with fixed ecotaxes """
        self.product.manual_fixed_ecotaxe = 1.5
        self.product._compute_ecotaxe()
        self.assertEqual(self.product.ecotaxe_amount, 1.5)
        self.invoice_line1.quantity = 4
        self.invoice._onchange_invoice_line_ids()
        self.assertEqual(self.invoice_line1.unit_ecotaxe_amount, 1.5)
        self.assertEqual(self.invoice_line1.subtotal_ecotaxe, 6.0)
        self.assertEqual(self.invoice.amount_total, 400.0)
        self.assertEqual(self.invoice.amount_ecotaxe, 6.0)

    def test_02_classification_weight_based_ecotaxe(self):
        """ Tests multiple lines with weight based ecotaxes """
        self.product.ecotaxe_classification_id = self.ecotaxe_classification2
        self.product._compute_ecotaxe()
        self.assertEqual(self.product.ecotaxe_amount, 4)
        self.invoice_line1.quantity = 3
        self.invoice._onchange_invoice_line_ids()
        self.assertEqual(self.invoice_line1.unit_ecotaxe_amount, 4)
        self.assertEqual(self.invoice_line1.subtotal_ecotaxe, 12)
        self.assertEqual(self.invoice.amount_total, 300.0)
        self.assertEqual(self.invoice.amount_ecotaxe, 12)

    def test_03_classification_ecotaxe(self):
        """ Tests multiple lines with mixed ecotaxes """
        self.product.ecotaxe_classification_id = self.ecotaxe_classification1
        self.product._compute_ecotaxe()
        self.assertEqual(self.product.ecotaxe_amount, 2.4)
        self.invoice_line1.quantity = 3
        self.invoice._onchange_invoice_line_ids()
        self.invoice_line2 = self.invoice_line.create(
            {
                "invoice_id": self.invoice.id,
                "name": "Line 1",
                "price_unit": 2000,
                "product_id": self.product2.product_variant_ids[:1].id,
                "account_id": self.account.id,
                "quantity": 2,
            }
        )
        self.invoice._onchange_invoice_line_ids()
        self.assertEqual(self.invoice_line1.unit_ecotaxe_amount, 2.4)
        self.assertEqual(self.invoice_line1.subtotal_ecotaxe, 7.2)
        self.assertEqual(self.invoice_line2.unit_ecotaxe_amount, 16)
        self.assertEqual(self.invoice_line2.subtotal_ecotaxe, 32)
        self.assertEqual(self.invoice.amount_total, 4300.0)
        self.assertEqual(self.invoice.amount_ecotaxe, 39.2)
