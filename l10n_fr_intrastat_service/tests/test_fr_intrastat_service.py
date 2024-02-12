# Copyright 2016-2020 Akretion France (http://www.akretion.com/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# @author: Alexis de Lattre <alexis.delattre@akretion.com>

import base64
from datetime import datetime

from dateutil.relativedelta import relativedelta
from lxml import etree

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import float_compare

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestFrIntrastatService(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.fr_test_company = cls.setup_company_data(
            "Akretion France",
            chart_template=chart_template_ref,
            country_id=cls.env.ref("base.fr").id,
            vat="FR86792377731",
        )
        cls.company = cls.fr_test_company["company"]
        cls.user.write(
            {
                "company_ids": [Command.link(cls.company.id)],
                "company_id": cls.company.id,
            }
        )
        cls.fp_eu_b2b = cls.env["account.fiscal.position"].create(
            {
                "name": "EU B2B",
                "intrastat": "b2b",
                "vat_required": True,
                "company_id": cls.company.id,
            }
        )
        cls.move_model = cls.env["account.move"]
        cls.account_account_model = cls.env["account.account"]
        cls.service_product = cls.env["product.product"].create(
            {
                "name": "Engineering services",
                "type": "service",
                "company_id": cls.company.id,
            }
        )
        cls.hw_product = cls.env["product.product"].create(
            {
                "name": "Hardware product",
                "type": "consu",
                "company_id": cls.company.id,
            }
        )

        cls.belgian_partner = cls.env["res.partner"].create(
            {
                "name": "Odoo SA",
                "is_company": True,
                "vat": "BE0477472701",
                "country_id": cls.env.ref("base.be").id,
                "company_id": False,
            }
        )
        cls.account_revenue = cls.fr_test_company["default_account_revenue"]

        # create first invoice
        date = datetime.today() + relativedelta(day=5, months=-1)
        inv1 = cls.move_model.create(
            {
                "company_id": cls.company.id,
                "partner_id": cls.belgian_partner.id,
                "fiscal_position_id": cls.fp_eu_b2b.id,
                "currency_id": cls.env.ref("base.EUR").id,
                "move_type": "out_invoice",
                "invoice_date": date,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.service_product.id,
                            "quantity": 5,
                            "price_unit": 90,
                            "name": "Audit service",
                            "account_id": cls.account_revenue.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            # product
                            "product_id": cls.hw_product.id,
                            "quantity": 1,
                            "price_unit": 1950,
                            "name": "Laptop",
                            "account_id": cls.account_revenue.id,
                        },
                    ),
                ],
            }
        )
        inv1.action_post()
        # create 2nd invoice
        inv2 = cls.move_model.create(
            {
                "company_id": cls.company.id,
                "partner_id": cls.belgian_partner.id,
                "fiscal_position_id": cls.fp_eu_b2b.id,
                "currency_id": cls.env.ref("base.EUR").id,
                "move_type": "out_invoice",
                "invoice_date": date,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.env.ref("product.product_product_1").id,
                            "quantity": 2,
                            "price_unit": 90.2,
                            "name": "GAP Analysis for your Odoo v10 project",
                            "account_id": cls.account_revenue.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            # consu product
                            "product_id": cls.env.ref("product.product_product_7").id,
                            "quantity": 1,
                            "price_unit": 45,
                            "name": "Apple headphones",
                            "account_id": cls.account_revenue.id,
                        },
                    ),
                ],
            }
        )
        inv2.action_post()
        # create refund
        inv3 = cls.move_model.create(
            {
                "company_id": cls.company.id,
                "partner_id": cls.belgian_partner.id,
                "fiscal_position_id": cls.fp_eu_b2b.id,
                "currency_id": cls.env.ref("base.EUR").id,
                "move_type": "out_refund",
                "invoice_date": date,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.service_product.id,
                            "quantity": 1,
                            "price_unit": 90,
                            "name": "Refund consulting hour",
                            "account_id": cls.account_revenue.id,
                        },
                    )
                ],
            }
        )
        inv3.action_post()

    def test_generate_des(self):
        des = self.env["l10n.fr.intrastat.service.declaration"].create(
            {"company_id": self.company.id}
        )
        des.generate_service_lines()
        self.assertFalse(float_compare(des.total_amount, 540.0, precision_digits=0))
        self.assertEqual(des.num_decl_lines, 3)
        des.done()
        self.assertEqual(des.state, "done")
        xml_des_file = des.attachment_id
        self.assertTrue(xml_des_file)
        self.assertEqual(xml_des_file.name[-4:], ".xml")
        xml_str = base64.b64decode(xml_des_file.datas)
        xml_root = etree.fromstring(xml_str)
        company_vat_xpath = xml_root.xpath("/fichier_des/declaration_des/num_tvaFr")
        self.assertEqual(company_vat_xpath[0].text, self.company.vat)
        lines_xpath = xml_root.xpath("/fichier_des/declaration_des/ligne_des")
        self.assertEqual(len(lines_xpath), des.num_decl_lines)
        with self.assertRaises(UserError):
            des.unlink()
        des.back2draft()
        self.assertEqual(des.state, "draft")

    def test_cron(self):
        self.env["l10n.fr.intrastat.service.declaration"].sudo()._scheduler_reminder()
