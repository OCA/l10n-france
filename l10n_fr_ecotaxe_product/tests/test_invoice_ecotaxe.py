# Copyright 2021 Camptocamp
#   @author Silvio Gregorini <silvio.gregorini@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from random import choice

from odoo.tests.common import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from .common import get_ecotax_cls


# Using TestProductCommon to access `init_invoice` already defined in there
@tagged("post_install", "-at_install")
class TestProductEcotaxe(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref)
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # ECOTAXES
        # 1- Fixed ecotax
        cls.ecotax_fixed = get_ecotax_cls(
            cls.env,
            "fixed",
            search_domain=[("company_id", "=", cls.env.user.company_id.id)],
        )
        # 2- Fixed ecotax
        cls.ecotax_weight = get_ecotax_cls(
            cls.env,
            "weight_based",
            search_domain=[("company_id", "=", cls.env.user.company_id.id)],
        )

        # ACCOUNTING STUFF
        # 1- Tax account
        cls.invoice_tax_account = cls.env["account.account"].create(
            {
                "code": "invoice_tax_account",
                "name": "Invoice Tax Account",
                "user_type_id": cls.env.ref("account.data_account_type_revenue").id,
                "company_id": cls.env.user.company_id.id,
            }
        )
        # 2- Invoice tax with included price to avoid unwanted amounts in tests
        cls.invoice_tax = cls.env["account.tax"].create(
            {
                "name": "Tax 10%",
                "price_include": True,
                "type_tax_use": "sale",
                "company_id": cls.env.user.company_id.id,
                "amount": 10,
                "tax_exigibility": "on_invoice",
                "invoice_repartition_line_ids": [
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": cls.invoice_tax_account.id,
                        },
                    ),
                ],
                "refund_repartition_line_ids": [
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": cls.invoice_tax_account.id,
                        },
                    ),
                ],
            }
        )

        # MISC
        # 1- Invoice partner
        cls.invoice_partner = cls.env["res.partner"].create({"name": "Test"})

    @classmethod
    def _create_invoice(cls, products):
        """Creates a new customer invoice with given products and returns it"""
        return cls.init_invoice(
            "out_invoice",
            partner=cls.invoice_partner,
            products=products,
            company=cls.env.user.company_id,
            taxes=cls.invoice_tax,
        )

    @classmethod
    def _create_product(cls, ecotax_classification):
        """Creates a product template with given ecotax classification

        Returns the newly created template variant
        """
        tmpl = cls.env["product.template"].create(
            {
                "name": " - ".join(["Product", ecotax_classification.name]),
                "ecotaxe_classification_id": ecotax_classification.id,
                # For the sake of simplicity, every product will have a price
                # and weight of 100
                "list_price": 100.00,
                "weight": 100.00,
            }
        )
        return tmpl.product_variant_ids[0]

    @staticmethod
    def _set_invoice_lines_random_quantities(invoice) -> list:
        """For each invoice line, sets a random qty between 1 and 10

        Returns the list of new quantities as a list
        """
        new_qtys = []
        random_qtys = tuple(range(1, 11))
        with Form(invoice) as invoice_form:
            for index in range(len(invoice.invoice_line_ids)):
                with invoice_form.invoice_line_ids.edit(index) as line_form:
                    new_qty = choice(random_qtys)
                    line_form.quantity = new_qty
                    new_qtys.insert(index, new_qty)
                line_form.save()
        invoice_form.save()
        return new_qtys

    def _run_checks(self, inv, inv_expected_amounts, inv_lines_expected_amounts):
        self.assertEqual(inv.amount_ecotaxe, inv_expected_amounts["amount_ecotaxe"])
        self.assertEqual(inv.amount_total, inv_expected_amounts["amount_total"])
        self.assertEqual(len(inv.invoice_line_ids), len(inv_lines_expected_amounts))
        for inv_line, inv_line_expected_amounts in zip(
            inv.invoice_line_ids, inv_lines_expected_amounts
        ):
            self.assertEqual(
                inv_line.unit_ecotaxe_amount,
                inv_line_expected_amounts["unit_ecotaxe_amount"],
            )
            self.assertEqual(
                inv_line.subtotal_ecotaxe, inv_line_expected_amounts["subtotal_ecotaxe"]
            )

    def test_01_default_fixed_ecotax(self):
        """Test default fixed ecotax

        Ecotax classification data for this test:
            - fixed type
            - default amount: 5.0
        Product data for this test:
            - list price: 100
            - fixed ecotax
            - no manual amount

        Expected results (with 1 line and qty = 1):
            - invoice ecotax amount: 5.0
            - invoice total amount: 100.0
            - line ecotax unit amount: 5.0
            - line ecotax total amount: 5.0
        """
        invoice = self._create_invoice(products=self._create_product(self.ecotax_fixed))
        self._run_checks(
            invoice,
            {"amount_ecotaxe": 5.0, "amount_total": 100.0},
            [{"unit_ecotaxe_amount": 5.0, "subtotal_ecotaxe": 5.0}],
        )
        new_qty = self._set_invoice_lines_random_quantities(invoice)[0]
        self._run_checks(
            invoice,
            {"amount_ecotaxe": 5.0 * new_qty, "amount_total": 100.0 * new_qty},
            [{"unit_ecotaxe_amount": 5.0, "subtotal_ecotaxe": 5.0 * new_qty}],
        )

    def test_02_manual_fixed_ecotax(self):
        """Test manual fixed ecotax

        Ecotax classification data for this test:
            - fixed type
            - default amount: 5.0
        Product data for this test:
            - list price: 100
            - fixed ecotax
            - manual amount: 10

        Expected results (with 1 line and qty = 1):
            - invoice ecotax amount: 10.0
            - invoice total amount: 100.0
            - line ecotax unit amount: 10.0
            - line ecotax total amount: 10.0
        """
        product = self._create_product(self.ecotax_fixed)
        product.manual_fixed_ecotaxe = 10
        invoice = self._create_invoice(products=product)
        self._run_checks(
            invoice,
            {"amount_ecotaxe": 10.0, "amount_total": 100.0},
            [{"unit_ecotaxe_amount": 10.0, "subtotal_ecotaxe": 10.0}],
        )
        new_qty = self._set_invoice_lines_random_quantities(invoice)[0]
        self._run_checks(
            invoice,
            {"amount_ecotaxe": 10.0 * new_qty, "amount_total": 100.0 * new_qty},
            [{"unit_ecotaxe_amount": 10.0, "subtotal_ecotaxe": 10.0 * new_qty}],
        )

    def test_03_weight_based_ecotax(self):
        """Test weight based ecotax

        Ecotax classification data for this test:
            - weight based type
            - coefficient: 0.04
        Product data for this test:
            - list price: 100
            - weight based ecotax
            - weight: 100

        Expected results (with 1 line and qty = 1):
            - invoice ecotax amount: 4.0
            - invoice total amount: 100.0
            - line ecotax unit amount: 4.0
            - line ecotax total amount: 4.0
        """
        invoice = self._create_invoice(
            products=self._create_product(self.ecotax_weight)
        )
        self._run_checks(
            invoice,
            {"amount_ecotaxe": 4.0, "amount_total": 100.0},
            [{"unit_ecotaxe_amount": 4.0, "subtotal_ecotaxe": 4.0}],
        )
        new_qty = self._set_invoice_lines_random_quantities(invoice)[0]
        self._run_checks(
            invoice,
            {"amount_ecotaxe": 4.0 * new_qty, "amount_total": 100.0 * new_qty},
            [{"unit_ecotaxe_amount": 4.0, "subtotal_ecotaxe": 4.0 * new_qty}],
        )

    def test_04_mixed_ecotax(self):
        """Test mixed ecotax within the same invoice

        Creating an invoice with 3 lines (one per type with types tested above)

        Expected results (with 3 lines and qty = 1):
            - invoice ecotax amount: 19.0
            - invoice total amount: 300.0
            - line ecotax unit amount (fixed ecotax): 5.0
            - line ecotax total amount (fixed ecotax): 5.0
            - line ecotax unit amount (manual ecotax): 10.0
            - line ecotax total amount (manual ecotax): 10.0
            - line ecotax unit amount (weight based ecotax): 4.0
            - line ecotax total amount (weight based ecotax): 4.0
        """
        default_fixed_product = self._create_product(self.ecotax_fixed)
        manual_fixed_product = self._create_product(self.ecotax_fixed)
        manual_fixed_product.manual_fixed_ecotaxe = 10
        weight_based_product = self._create_product(self.ecotax_weight)
        invoice = self._create_invoice(
            products=default_fixed_product | manual_fixed_product | weight_based_product
        )
        self._run_checks(
            invoice,
            {"amount_ecotaxe": 19.0, "amount_total": 300.0},
            [
                {"unit_ecotaxe_amount": 5.0, "subtotal_ecotaxe": 5.0},
                {"unit_ecotaxe_amount": 10.0, "subtotal_ecotaxe": 10.0},
                {"unit_ecotaxe_amount": 4.0, "subtotal_ecotaxe": 4.0},
            ],
        )
        new_qtys = self._set_invoice_lines_random_quantities(invoice)
        self._run_checks(
            invoice,
            {
                "amount_ecotaxe": 5.0 * new_qtys[0]
                + 10.0 * new_qtys[1]
                + 4.0 * new_qtys[2],
                "amount_total": 100.0 * sum(new_qtys),
            },
            [
                {"unit_ecotaxe_amount": 5.0, "subtotal_ecotaxe": 5.0 * new_qtys[0]},
                {"unit_ecotaxe_amount": 10.0, "subtotal_ecotaxe": 10.0 * new_qtys[1]},
                {"unit_ecotaxe_amount": 4.0, "subtotal_ecotaxe": 4.0 * new_qtys[2]},
            ],
        )
