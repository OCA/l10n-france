# © 2022 David BEAL @ Akretion
# © 2022 Alexis DE LATTRE @ Akretion

# from odoo import fields
# from odoo.tests import tagged
from odoo.tests.common import TransactionCase
# from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from odoo.tests import tagged


# class Test(AccountTestInvoicingCommon):
# @tagged("standard")
# @tagged("+nice")
@tagged("-at_install", "post_install")
class TestB(TransactionCase):

    # @classmethod
    # def setUpClass(cls):
    #     super().setUpClass()
    #     cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
    #     cls.user_model = cls.env["res.users"].with_context(no_reset_password=True)
    #     cls.patch(type(cls.env["res.partner"]), "_get_gravatar_image", lambda *a: False)

    def setUp(self):
        super().setUp()
        import pdb; pdb.set_trace()
        self.env = self.env(context=dict(self.env.context, tracking_disable=True))
        self.pp = "PP"

    def test_module(self):
        import pdb; pdb.set_trace()
        company = self.env['res.company']._create_french_company(company_name="Any")
        assert len(company) == 1
        # partner = self.partner_a
        # tax = self.tax_sale_a
        # today = fields.Date.today()
        # self.init_invoice(
        #     "in_invoice",
        #     partner=partner,
        #     invoice_date=today,
        #     post=True,
        #     amounts=[100],
        #     taxes=tax,
        #     company=company,
        # )
