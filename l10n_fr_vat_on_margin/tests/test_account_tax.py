from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError

from odoo import fields
from odoo.fields import Command
from odoo.tests import Form, tagged
from odoo.tools import float_is_zero

@tagged('post_install', '-at_install')
class TestAccountTax(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_fr.l10n_fr_pcg_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        # Launch test with root user
        cls.env = cls.env(user=cls.env.ref('base.user_root'))
        # The taxes are no longer a single xmlid'd record: loading the French
        # chart generates one per company. Looking it up by name on the test
        # company is what proves that generation happened at all.
        cls.margin_tax = cls.env['account.tax'].search([
            ('name', '=', 'TVA sur marge 20% TTC - Vente'),
            ('company_id', '=', cls.env.company.id),
        ], limit=1)
        assert cls.margin_tax, "The margin tax was not generated for the company"



    def test_tva_on_margin_service(self):

        seller = self.env['res.partner'].create({
            'name': 'Seller',
            'street': 'Seller street',
            'city': 'Seller city',
            'zip': 'Seller zip',
            'country_id': self.env
            .ref('base.fr').id,
        })

        '''Test the computation of the VAT on margin for a sale.order.line'''
        #     Create a product that will be used
        product = self.env['product.product'].create({
            'name': 'Test TVA',
            'type': 'service',
            'service_to_purchase': True,
            'vat_on_margin': True,
            'seller_ids': [(0, 0, {
                'partner_id': seller.id,
                'price': 110,
            })]
        })


        sale_order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.partner_admin').id,
            'order_line': [
                Command.create(
                    {
                        'product_id': product.id,
                        'vendor_id': seller.id,
                        'product_uom_qty': 1,
                        'price_unit': 150,
                        'purchase_price': 110,
                        'margin': 40,
                        'tax_id': [(6, 0, self.margin_tax.ids)],
                    }
                )
            ],
        })

        sale_order.action_confirm()

        # Sold 150, bought 110: the margin is 110 -> 150, i.e. 40, and under the
        # margin scheme (art. 297 A CGI) that margin is a VAT-inclusive amount.
        # The VAT is therefore extracted from it: 40 * 20 / 120 = 6.67, never
        # 40 * 20% = 8, which would treat the margin as a tax-excluded amount.
        self.assertEqual(sale_order.amount_tax, 6.67, 'The tax amount is wrong')
        self.assertEqual(sale_order.amount_total, 150, 'The total amount is wrong')
        self.assertEqual(sale_order.amount_untaxed, 143.33, 'The untaxed amount is wrong')


    def test_tva_on_margin_consu(self):

        seller = self.env['res.partner'].create({
            'name': 'Seller',
            'street': 'Seller street',
            'city': 'Seller city',
            'zip': 'Seller zip',
            'country_id': self.env
            .ref('base.fr').id,
        })

        product_consu = self.env['product.product'].create({
            'name': 'Test TVA 2',
            'type': 'consu',
            'service_to_purchase': True,
            'vat_on_margin': True,
            'seller_ids': [(0, 0, {
                'partner_id': seller.id,
                'price': 110,
            })]
        })

        sale_order_consu = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.partner_admin').id,
            'order_line': [
                Command.create(
                    {
                        'product_id': product_consu.id,
                        'vendor_id': seller.id,
                        'product_uom_qty': 1,
                        'price_unit': 150,
                        'purchase_price': 110,
                        'margin': 40,
                        'tax_id': [(6, 0, self.margin_tax.ids)],
                    }
                )
            ],
        })

        sale_order_consu.action_confirm()

        # Same margin as the service case: 40 VAT-inclusive, so 40 * 20 / 120.
        self.assertEqual(sale_order_consu.amount_tax, 6.67, 'The tax amount is wrong')
        self.assertEqual(sale_order_consu.amount_total, 150, 'The total amount is wrong')
        self.assertEqual(sale_order_consu.amount_untaxed, 143.33, 'The untaxed amount is wrong')

        account_move = sale_order_consu._create_invoices()

        # The margin must survive the sale order -> invoice hand-off.
        self.assertEqual(account_move.amount_total, 150, 'The total amount is wrong')
        self.assertEqual(account_move.amount_tax, 6.67, 'The tax amount is wrong')
        self.assertEqual(account_move.amount_untaxed, 143.33, 'The untaxed amount is wrong')
        self.assertEqual(account_move.amount_residual, 150, 'The residual amount is wrong')
