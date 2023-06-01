# © 2021-2023 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestsaleEcotaxe(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=""):
        super(TestsaleEcotaxe, cls).setUpClass(chart_template_ref)

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

    def create_sale_partner(self, partner_id, product_id, sale_amount=0.00):
        order = self.env["sale.order"].create(
            {
                "partner_id": partner_id.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product_id.id,
                            "product_uom_qty": 1,
                            "price_unit": sale_amount,
                        },
                    )
                ],
            }
        )

        return order

    def test_01_manual_fixed_ecotaxe(self):
        """Tests multiple lines with fixed ecotaxes"""
        # in order to test the correct assignment of fixed ecotaxe
        # I create a customer sale.
        partner12 = self.env.ref("base.res_partner_12")
        self.sale = self.create_sale_partner(
            sale_amount=100.00, partner_id=partner12, product_id=self.product_a
        )
        # I assign a product with fixed ecotaxte to sale line
        self.sale_line1 = self.sale.order_line[0]
        self.product_a.manual_fixed_ecotaxe = 1.5
        # make sure to have 1 tax and fix tax rate
        self.sale_line1.tax_id = self.sale_line1.tax_id[0]
        self.sale_line1.tax_id.amount = 20
        self.sale_line1._compute_ecotaxe()
        self.assertEqual(self.product_a.ecotaxe_amount, 1.5)
        self.sale_line1.product_uom_qty = 4
        self.sale_line1._onchange_product_packaging_id()
        self.assertEqual(self.sale_line1.unit_ecotaxe_amount, 1.5)
        self.assertEqual(self.sale_line1.subtotal_ecotaxe, 6.0)
        self.assertEqual(self.sale.amount_total, 4800.0)
        self.assertEqual(self.sale.amount_ecotaxe, 6.0)

    def test_02_classification_weight_based_ecotaxe(self):
        """Tests multiple lines with weight based ecotaxes"""
        # in order to test the correct assignment of fixed ecotaxe
        # I create a customer sale.
        partner12 = self.env.ref("base.res_partner_12")
        self.sale = self.create_sale_partner(
            sale_amount=100.00, partner_id=partner12, product_id=self.product_b
        )
        # I assign a product with fixed ecotaxte to sale line
        self.sale_line1 = self.sale.order_line[0]
        # make sure to have 1 tax and fix tax rate
        self.sale_line1.tax_id = self.sale_line1.tax_id[0]
        self.sale_line1.tax_id.amount = 20
        self.sale_line1._compute_ecotaxe()
        self.assertEqual(self.product_b.ecotaxe_amount, 16)
        self.sale_line1.product_uom_qty = 3
        self.assertEqual(self.sale_line1.unit_ecotaxe_amount, 16)
        self.assertEqual(self.sale_line1.subtotal_ecotaxe, 48)
        self.assertEqual(self.sale.amount_total, 720.0)
        self.assertEqual(self.sale.amount_ecotaxe, 48)

    def test_03_classification_ecotaxe(self):
        """Tests multiple lines with mixed ecotaxes"""
        # in order to test the correct assignment of fixed ecotaxe
        # I create a customer sale.
        partner12 = self.env.ref("base.res_partner_12")
        self.sale = self.create_sale_partner(
            sale_amount=100.00, partner_id=partner12, product_id=self.product_a
        )
        # add line to SO
        self.env["sale.order.line"].create(
            {
                "product_id": self.product_b.id,
                "product_uom_qty": 2,
                "price_unit": 100,
                "order_id": self.sale.id,
            },
        )
        # I assign a product with fixed ecotaxte to sale line
        self.sale_line1 = self.sale.order_line[0]
        # make sure to have 1 tax and fix tax rate
        self.sale_line1.tax_id = self.sale_line1.tax_id[0]
        self.sale_line1.tax_id.amount = 20
        self.sale_line2 = self.sale.order_line[1]
        # make sure to have 1 tax and fix tax rate
        self.sale_line2.tax_id = self.sale_line1.tax_id[0]
        self.sale_line2.tax_id.amount = 20
        self.sale_line1._compute_ecotaxe()
        self.assertEqual(self.product_a.ecotaxe_amount, 2.4)
        self.sale_line1.product_uom_qty = 3
        self.sale_line1._onchange_product_packaging_id()
        self.assertEqual(self.sale_line1.unit_ecotaxe_amount, 2.4)
        self.assertAlmostEqual(self.sale_line1.subtotal_ecotaxe, 7.2)
        self.assertEqual(self.sale_line2.unit_ecotaxe_amount, 16)
        self.assertEqual(self.sale_line2.subtotal_ecotaxe, 32)
        self.assertEqual(self.sale.amount_total, 3840.0)
        self.assertEqual(self.sale.amount_ecotaxe, 39.2)
