# Copyright 2016-2020 Akretion France (http://www.akretion.com/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# @author: Alexis de Lattre <alexis.delattre@akretion.com>

import base64
from datetime import datetime

from dateutil.relativedelta import relativedelta
from lxml import etree

from odoo.tests.common import TransactionCase
from odoo.tools import float_compare


class TestFrIntrastatService(TransactionCase):
    def setUp(self):
        super(TestFrIntrastatService, self).setUp()
        # Set company country to France
        # Using base.main_company is more difficult now because
        # its currency is USD
        # So I decided to create another company from scratch
        self.company = self.env["res.company"].create(
            {
                "name": "Akretion France",
                "street": "27 rue Henri Rolland",
                "zip": "69100",
                "city": "Villeurbanne",
                "country_id": self.env.ref("base.fr").id,
                "vat": "FR86792377731",
            }
        )
        self.env.company.chart_template_id.try_loading(company=self.company)
        self.env.user.write({"company_ids": [(4, self.company.id)]})
        self.env.user.write({"company_id": self.company.id})
        self.fp_eu_b2b = self.env["account.fiscal.position"].create(
            {
                "name": "EU B2B",
                "intrastat": True,
            }
        )
        self.move_model = self.env["account.move"]
        self.move_line_model = self.env["account.move.line"]
        self.account_account_model = self.env["account.account"]
        self.service_product = self.env["product.product"].create(
            {
                "name": "Engineering services",
                "type": "service",
                "company_id": self.company.id,
            }
        )
        self.hw_product = self.env["product.product"].create(
            {
                "name": "Hardware product",
                "type": "consu",
                "company_id": self.company.id,
            }
        )

        self.belgian_partner = self.env["res.partner"].create(
            {
                "name": "Odoo SA",
                "is_company": True,
                "vat": "BE0477472701",
                "country_id": self.env.ref("base.be").id,
                "company_id": False,
            }
        )
        self.account_receivable = self.account_account_model.search(
            [("code", "=", "411100"), ("company_id", "=", self.company.id)], limit=1
        )
        if not self.account_receivable:
            self.account_receivable = self.account_account_model.create(
                {
                    "code": "411100",
                    "name": "Debtors - (test)",
                    "reconcile": True,
                    "user_type_id": self.ref("account.data_account_type_receivable"),
                    "company_id": self.company.id,
                }
            )
        assert self.account_receivable
        self.account_revenue = self.account_account_model.search(
            [("code", "=", "706000"), ("company_id", "=", self.company.id)], limit=1
        )
        if not self.account_revenue:
            self.account_revenue = self.account_account_model.create(
                {
                    "code": "706000",
                    "name": "Service Sales - (test)",
                    "user_type_id": self.ref("account.data_account_type_revenue"),
                    "company_id": self.company.id,
                }
            )

        # create first invoice
        date = datetime.today() + relativedelta(day=5, months=-1)
        inv1 = self.move_model.create(
            {
                "company_id": self.company.id,
                "partner_id": self.belgian_partner.id,
                "fiscal_position_id": self.fp_eu_b2b.id,
                "currency_id": self.env.ref("base.EUR").id,
                "move_type": "out_invoice",
                "invoice_date": date,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.service_product.id,
                            "quantity": 5,
                            "price_unit": 90,
                            "name": "Audit service",
                            "account_id": self.account_revenue.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            # product
                            "product_id": self.hw_product.id,
                            "quantity": 1,
                            "price_unit": 1950,
                            "name": "Laptop",
                            "account_id": self.account_revenue.id,
                        },
                    ),
                ],
            }
        )
        inv1.action_post()
        # create 2nd invoice
        inv2 = self.move_model.create(
            {
                "company_id": self.company.id,
                "partner_id": self.belgian_partner.id,
                "fiscal_position_id": self.fp_eu_b2b.id,
                "currency_id": self.env.ref("base.EUR").id,
                "move_type": "out_invoice",
                "invoice_date": date,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.env.ref("product.product_product_1").id,
                            "quantity": 2,
                            "price_unit": 90.2,
                            "name": "GAP Analysis for your Odoo v10 project",
                            "account_id": self.account_revenue.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            # consu product
                            "product_id": self.env.ref("product.product_product_7").id,
                            "quantity": 1,
                            "price_unit": 45,
                            "name": "Apple headphones",
                            "account_id": self.account_revenue.id,
                        },
                    ),
                ],
            }
        )
        inv2.action_post()
        # create refund
        inv3 = self.move_model.create(
            {
                "company_id": self.company.id,
                "partner_id": self.belgian_partner.id,
                "fiscal_position_id": self.fp_eu_b2b.id,
                "currency_id": self.env.ref("base.EUR").id,
                "move_type": "out_refund",
                "invoice_date": date,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.service_product.id,
                            "quantity": 1,
                            "price_unit": 90,
                            "name": "Refund consulting hour",
                            "account_id": self.account_revenue.id,
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
        self.assertEqual(float_compare(des.total_amount, 540.0, precision_digits=0), 0)
        self.assertEqual(des.num_decl_lines, 3)
        des.done()
        self.assertEqual(des.state, "done")
        des.generate_xml()
        xml_des_file = des.attachment_id
        self.assertTrue(xml_des_file)
        self.assertEqual(xml_des_file.name[-4:], ".xml")
        xml_str = base64.b64decode(xml_des_file.datas)
        xml_root = etree.fromstring(xml_str)
        company_vat_xpath = xml_root.xpath("/fichier_des/declaration_des/num_tvaFr")
        self.assertEqual(company_vat_xpath[0].text, self.company.vat)
        lines_xpath = xml_root.xpath("/fichier_des/declaration_des/ligne_des")
        self.assertEqual(len(lines_xpath), des.num_decl_lines)
