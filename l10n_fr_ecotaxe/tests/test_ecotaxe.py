# © 2021 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestInvoiceEcotaxe(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super(TestInvoiceEcotaxe, cls).setUpClass()

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
        cls.product_a.weight = 100
        cls.product_a.ecotaxe_classification_id = cls.ecotaxe_classification1.id
        cls.product_b.weight = 400
        cls.product_b.ecotaxe_classification_id = cls.ecotaxe_classification2.id

    def test_01_manual_fixed_ecotaxe(self):
        """Tests multiple lines with fixed ecotaxes"""
        # in order to test the correct assignment of fixed ecotaxe
        # I create a customer invoice.
        partner12 = self.env.ref("base.res_partner_12")
        invoice = self.init_invoice(
            "in_invoice",
            partner=partner12,
            amounts=[
                100.00,
            ],
        )
        # I assign a product with fixed ecotaxte to invoice line
        move_line1 = invoice.invoice_line_ids[0]
        move_line1.product_id = self.product_a
        self.product_a.manual_fixed_ecotaxe = 1.5
        self.assertEqual(self.product_a.ecotaxe_amount, 1.5)
        move_line1.quantity = 4
        invoice._onchange_invoice_line_ids()
        self.assertEqual(move_line1.unit_ecotaxe_amount, 1.5)
        self.assertEqual(move_line1.subtotal_ecotaxe, 6.0)
        self.assertEqual(invoice.amount_total, 400.0)
        self.assertEqual(invoice.amount_ecotaxe, 6.0)

    def test_02_classification_weight_based_ecotaxe(self):
        """Tests multiple lines with weight based ecotaxes"""
        # in order to test the correct assignment of fixed ecotaxe
        # I create a customer invoice.
        partner12 = self.env.ref("base.res_partner_12")
        invoice = self.init_invoice(
            "in_invoice",
            partner=partner12,
            amounts=[
                100.00,
            ],
        )
        # I assign a product with fixed ecotaxte to invoice line
        move_line1 = invoice.invoice_line_ids[0]
        move_line1.product_id = self.product_b

        self.assertEqual(self.product_b.ecotaxe_amount, 16)
        move_line1.quantity = 3
        invoice._onchange_invoice_line_ids()
        self.assertEqual(move_line1.unit_ecotaxe_amount, 4)
        self.assertEqual(move_line1.subtotal_ecotaxe, 12)
        self.assertEqual(invoice.amount_total, 300.0)
        self.assertEqual(invoice.amount_ecotaxe, 12)

    def test_03_classification_ecotaxe(self):
        """Tests multiple lines with mixed ecotaxes"""
        # in order to test the correct assignment of fixed ecotaxe
        # I create a customer invoice.
        partner12 = self.env.ref("base.res_partner_12")
        invoice = self.init_invoice(
            "in_invoice",
            partner=partner12,
            amounts=[
                100.00,
            ],
        )
        # I assign a product with fixed ecotaxte to invoice line
        move_line1 = invoice.invoice_line_ids[0]
        move_line1.product_id = self.product_a

        self.assertEqual(self.product_a.ecotaxe_amount, 2.4)
        move_line1.quantity = 3
        invoice._onchange_invoice_line_ids()
        move_line2 = move_line1.create(
            {
                "move_id": invoice.id,
                "name": "Line 1",
                "price_unit": 2000,
                "product_id": self.product_b.id,
                "quantity": 2,
            }
        )
        invoice._onchange_invoice_line_ids()
        self.assertEqual(move_line1.unit_ecotaxe_amount, 2.4)
        self.assertEqual(move_line1.subtotal_ecotaxe, 7.2)
        self.assertEqual(move_line2.unit_ecotaxe_amount, 16)
        self.assertEqual(move_line2.subtotal_ecotaxe, 32)
        self.assertEqual(invoice.amount_total, 4300.0)
        self.assertEqual(invoice.amount_ecotaxe, 39.2)
