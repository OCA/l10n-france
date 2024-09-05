# Copyright 2024 Akretion (http://www.akretion.com).
# @author Thomas BONNERUE <thomas.bonnerue@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import rsa

from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentAcquirerCommon


class PayboxTest(PaymentAcquirerCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.paybox = cls.env.ref("payment.payment_acquirer_paybox")
        (pubkey, privkey) = rsa.newkeys(1024)
        cls.paybox.write(
            {
                "state": "test",
                "paybox_ept": "1025480",
                "paybox_company_code": "dummy",
                "paybox_rang": "rang-04",
                "paybox_secret": "F4861FGAT65d4",
            }
        )

    def test_paybox_form_render(self):
        self.assertEqual(self.paybox.state, "test", "test without test environment")

    def test_paybox_form_management(self):
        self.assertEqual(self.paybox.state, "test", "test without test environment")

        # typical data posted by paybox after client has successfully paid
        paybox_post_data = "Mt=1000&Ref=18AB940&Auto=78594&\
            Response=00000&Date=250391&NumPBX=456&KEY="

        tx = self.env["payment.transaction"].create(
            {
                "amount": 10.00,
                "aquirer_id": self.paybox.id,
                "currency_id": self.currency_euro.id,
                "reference": "18AB940",
                "partner_name": "Norbert Buyer",
            }
        )

        tx.form_feedback(paybox_post_data, "paybox")
        self.assertEqual(tx.state, "done")
