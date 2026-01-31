# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from collections import defaultdict
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestFrAccountVatReturn(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.today = datetime.now().date()
        cls.start_date = cls.today + relativedelta(months=-1, day=1)
        cls.before_start_date = cls.start_date + relativedelta(days=-1)
        cls.end_date = cls.start_date + relativedelta(day=31)
        cls.first_creation_date = fields.Date.from_string("2022-01-01")
        cls.on_invoice_company = cls.env["res.company"]._test_fr_vat_create_company(
            company_name="FR Company VAT on_invoice", fr_vat_exigibility="on_invoice"
        )
        cls.on_payment_company = cls.env["res.company"]._test_fr_vat_create_company(
            company_name="FR Company VAT on_payment", fr_vat_exigibility="on_payment"
        )

    def _check_vat_return_result(self, vat_return, box_result, move_result):
        box2value = {}
        for line in vat_return.line_ids.filtered(
            lambda x: not x.box_display_type and x.box_edi_type == "MOA"
        ):
            box2value[(line.box_form_code, line.box_edi_code)] = line.value
        for box_xmlid, expected_value in box_result.items():
            box = self.env.ref(f"l10n_fr_account_vat_return.{box_xmlid}")
            real_valuebox = box2value.pop((box.form_code, box.edi_code))
            self.assertEqual(real_valuebox, expected_value)
        self.assertFalse(box2value)
        move = vat_return.move_id
        company = vat_return.company_id
        self.assertTrue(move)
        self.assertTrue(move.ref)
        if vat_return.state in ("auto", "sent"):
            self.assertEqual(move.state, "draft")
        elif vat_return.state == "posted":
            self.assertEqual(move.state, "posted")
        self.assertEqual(move.date, vat_return.end_date)
        self.assertEqual(move.journal_id, company.fr_vat_journal_id)

        currency = company.currency_id
        move_dict = defaultdict(float)
        for line in move.line_ids:
            move_dict[line.account_id.code] += line.balance
        for account_code, amount in move_result.items():
            self.assertFalse(currency.compare_amounts(move_dict[account_code], amount))
        # Check that 758 and 658 have an amount under 1 €
        self.assertEqual(
            currency.compare_amounts(move_dict.get("758000", 0) * -1, 1), -1
        )
        self.assertEqual(currency.compare_amounts(move_dict.get("658000", 0), 1), -1)

    def test_tax_fr_vat_autoliquidation(self):
        intracom_extracom_autoliq_taxes = (
            self.env["account.tax"]
            .with_context(active_test=False)
            .search(
                [
                    ("company_id", "=", self.on_invoice_company.id),
                    ("type_tax_use", "=", "purchase"),
                    ("amount", ">", 0),
                    ("unece_type_code", "=", "VAT"),
                    ("country_id", "=", self.env.ref("base.fr").id),
                    "|",
                    ("name", "ilike", "intracom"),
                    ("name", "ilike", "extracom"),
                ]
            )
        )
        self.assertTrue(len(intracom_extracom_autoliq_taxes) > 6)
        for tax in intracom_extracom_autoliq_taxes:
            self.assertEqual(tax.fr_vat_autoliquidation, "total")

    def test_vat_return_on_invoice(self):
        company = self.on_invoice_company
        aao = self.env["account.account"]
        currency = company.currency_id
        initial_credit_vat = 3333
        company._test_create_move_init_vat_credit(
            initial_credit_vat, self.before_start_date
        )
        company._test_create_invoice_data(self.start_date)
        vat_return = self.env["l10n.fr.account.vat.return"].create(
            {
                "company_id": company.id,
                "start_date": self.start_date,
                "vat_periodicity": "1",
            }
        )
        self.assertEqual(vat_return.end_date, self.end_date)
        self.assertEqual(vat_return.vat_on_payment_option, "non_native")
        self.assertEqual(vat_return.state, "manual")
        # Create a manual line without rate
        new_manual_account_id = aao.create(
            {
                "code": "635900",
                "name": "Taxe spécifique",
                "company_id": company.id,
                "account_type": "expense",
            }
        )
        self.env.ref("l10n_fr_account_vat_return.a_ud").with_company(company.id).write(
            {"account_id": new_manual_account_id}
        )
        self.env["l10n.fr.account.vat.return.line"].create(
            {
                "box_id": self.env.ref("l10n_fr_account_vat_return.a_ud").id,
                "value_manual_int": 134,
                "parent_id": vat_return.id,
            }
        )
        # Create another manual line with a rate
        existing_manual_account_id = aao.search(
            [
                ("code", "=", "635800"),
                ("company_id", "=", company.id),
                ("account_type", "=", "expense"),
            ],
            limit=1,
        )
        self.env.ref("l10n_fr_account_vat_return.a_kj").with_company(company.id).write(
            {"account_id": existing_manual_account_id}
        )
        self.env["l10n.fr.account.vat.return.line"].create(
            {
                "box_id": self.env.ref("l10n_fr_account_vat_return.a_mk").id,
                "value_manual_int": 1000,
                "parent_id": vat_return.id,
            }
        )
        vat_return.manual2auto()
        self.assertEqual(vat_return.state, "auto")
        box_result = {
            "ca3_ca": 51510,  # A
            "ca3_cb": 100,  # A2 France autoliq (for royalty)
            "ca3_kh": 2210,  # A3 HA intracom services
            "ca3_dk": 2810,  # A4 HA extracom products
            "ca3_cc": 2410,  # B2 HA intracom products
            "ca3_cg": 3900,  # B4 HA extracom services
            "ca3_da": 750,  # E1 Extracom
            "ca3_db": 1400,  # E2 Autres opérations non imposables
            "ca3_dc": 150,  # F2 livraisons intracom
            ######
            "ca3_fp": 530,  # base 20%
            "ca3_gp": 106,  # montant collecté 20%
            "ca3_fr": 700,  # base 10%
            "ca3_gr": 70,  # montant collecté 10%
            "ca3_fb": 27500,  # base 5,5%
            "ca3_gb": 1512,  # montant collecté 5,5%
            "ca3_mf": 31300,  # base 2,1%
            "ca3_me": 657,  # montant collecté 2,1%
            "ca3_lb": 200,  # base autoliq import 20%
            "ca3_lc": 40,  # montant autoliq import 20%
            "ca3_ld": 110,  # base autoliq import 10%
            "ca3_le": 11,  # montant autoliq import 10%
            "ca3_lh": 500,  # base autoliq import 5.5%
            "ca3_lj": 28,  # montant autoliq import 5.5%
            "ca3_lk": 2000,  # base autoliq import 2,1%
            "ca3_ll": 42,  # montant autoliq import 2,1%
            "ca3_mg": 100,  # base droits d'auteur
            "ca3_md": 9,  # montant droits d'auteur
            "ca3_gh": 2475,  # Total TVA collectée
            "ca3_gj": 141,  # dont TVA sur acquisitions intracom
            "ca3_gk": 891,  # dont TVA à Monaco
            ######
            "ca3_ha": 1065,  # TVA déduc immo
            "ca3_hb": 644,  # TVA déduc biens et services
            "ca3_hd": initial_credit_vat,  # report crédit TVA
            "ca3_hg": 5042,  # total VAT deduc
            ######
            "a_ud": 134,
            "a_mk": 1000,
            "a_kj": 52,
            "a_hb": 186,
            "ca3_kb": 186,  # Report taxes annexes
            "ca3_ke": 186,  # Total à payer
            "ca3_ja": 2567,  # credit TVA (ligne 23 - 16)
            "ca3_jc": 2567,  # crédit à reporter
        }
        move_result = {
            "445711": 46,
            "445712": 28,
            "445713": 1265,
            "445714": 588,
            "445620": -1065,
            "445660": -94.6,
            "445201": 40,
            "445202": 22,
            "445203": 110,
            "445204": 46.2,
            "445662": -218.2,
            "445301": 60,
            "445302": 31,
            "445303": 165,
            "445304": 65.1,
            "445663": -321.1,
            "445719": 9.2,
            "445669": -10,
            "447000": box_result["ca3_kb"] * -1,
            "445670": box_result["ca3_jc"] - box_result["ca3_hd"],
            "635800": box_result["a_kj"],
            "635900": box_result["a_ud"],
        }
        self._check_vat_return_result(vat_return, box_result, move_result)

        # Test reimbursement
        self.assertTrue(vat_return.reimbursement_show_button)
        reimbursement_type = "first"
        reimbursement_amount = 2000
        reimb_wiz = (
            self.env["l10n.fr.account.vat.return.reimbursement"]
            .with_context(
                active_model="l10n.fr.account.vat.return", active_id=vat_return.id
            )
            .create(
                {
                    "amount": reimbursement_amount,
                    "reimbursement_type": reimbursement_type,
                    "first_creation_date": self.first_creation_date,
                }
            )
        )
        reimb_wiz.validate()
        reimb_box_result = dict(box_result)
        reimb_box_result.update(
            {
                "ca3_jb": reimbursement_amount,
                "ca3_jc": box_result["ca3_jc"] - reimbursement_amount,
            }
        )
        reimb_move_result = dict(move_result)
        reimb_move_result.update(
            {
                "445830": reimbursement_amount,
                "445670": reimb_box_result["ca3_jc"] - initial_credit_vat,
            }
        )
        # 445670: Do not mix the balance of the move and the balance of the
        # account. The balance of the account must be equal to
        # reimb_box_result["ca3_jc"]
        self._check_vat_return_result(vat_return, reimb_box_result, reimb_move_result)
        self.assertEqual(vat_return.reimbursement_type, reimbursement_type)
        self.assertEqual(
            vat_return.reimbursement_first_creation_date, self.first_creation_date
        )
        # Remove reimbursement
        vat_return.remove_credit_vat_reimbursement()
        self._check_vat_return_result(vat_return, box_result, move_result)
        self.assertFalse(vat_return.reimbursement_type)
        self.assertFalse(vat_return.reimbursement_first_creation_date)
        vat_return.print_ca3()
        vat_return.auto2sent_manual()
        self.assertEqual(vat_return.state, "sent")
        self.assertTrue(vat_return.sent_datetime)
        vat_return.sent2posted()
        self.assertEqual(vat_return.state, "posted")
        self._check_vat_return_result(vat_return, box_result, move_result)
        speedy = vat_return._prepare_speedy()
        bal_zero_accounts = ["445711", "445712", "445713", "445714", "445715"]
        for acc_code in bal_zero_accounts:
            acc = aao.search(
                [("code", "=", acc_code), ("company_id", "=", company.id)], limit=1
            )
            self.assertTrue(acc)
            balance = acc._fr_vat_get_balance("base_domain_end", speedy)
            self.assertTrue(currency.is_zero(balance))
        must_be_reconciled = bal_zero_accounts + ["445620"]
        for line in vat_return.move_id.line_ids:
            if line.account_id.code in must_be_reconciled:
                self.assertTrue(line.full_reconcile_id)
        # The reimbursement has been removed, but we call generate_zip_deductible_vat()
        # just to make sure it works, even if it's not a real life scenario to call it
        # without a reimbursement
        action = vat_return.generate_zip_deductible_vat()
        self.assertTrue(vat_return.deductible_vat_zip_file_id)
        self.assertEqual(action.get("type"), "ir.actions.act_url")

    def test_vat_return_on_payment(self):
        aao = self.env["account.account"]
        lfavruvopmlo = self.env[
            "l10n.fr.account.vat.return.unpaid.vat.on.payment.manual.line"
        ]
        company = self.on_payment_company
        currency = company.currency_id
        initial_credit_vat = 22
        company._test_create_move_init_vat_credit(
            initial_credit_vat, self.before_start_date
        )
        company._test_create_invoice_data(self.start_date, extracom_refund_ratio=2)
        vat_return = self.env["l10n.fr.account.vat.return"].create(
            {
                "company_id": company.id,
                "start_date": self.start_date,
                "vat_periodicity": "1",
            }
        )
        self.assertEqual(vat_return.vat_on_payment_option, "non_native")
        manual_acc2amt = {
            "445711": 30,  # 20%
            "445712": 20,  # 10%
            "445713": 50,  # 5,5%
            "445660": 60,
        }
        for acc_code, amount in manual_acc2amt.items():
            account = aao.search(
                [("code", "=", acc_code), ("company_id", "=", company.id)], limit=1
            )
            self.assertTrue(account)
            lfavruvopmlo.create(
                {
                    "parent_id": vat_return.id,
                    "account_id": account.id,
                    "amount": amount,
                }
            )

        self.assertEqual(vat_return.end_date, self.end_date)
        self.assertEqual(vat_return.state, "manual")
        vat_return.manual2auto()
        self.assertEqual(vat_return.state, "auto")
        box_result = {
            "ca3_ca": 38889,  # A
            "ca3_cb": 100,  # A2 France autoliq (for royalty)
            "ca3_kh": 2210,  # A3 HA intracom services
            "ca3_dk": 2810,  # A4 HA extracom products
            "ca3_cc": 2410,  # B2 HA intracom products
            "ca3_cg": 3900,  # B4 HA extracom services
            "ca3_db": 1400,  # E2 Autres opérations non imposables
            "ca3_dc": 150,  # F2 livraisons intracom
            "ca3_de": 1500,  # F8 régularisations
            # => replaces E1 because the extracom amount is negative
            ######
            "ca3_fp": 338,  # base 20%
            "ca3_gp": 68,  # montant collecté 20%
            "ca3_fr": 430,  # base 10%
            "ca3_gr": 43,  # montant collecté 10%
            "ca3_fb": 22341,  # base 5,5%
            "ca3_gb": 1229,  # montant collecté 5,5%
            "ca3_mf": 24300,  # base 2,1%
            "ca3_me": 510,  # montant collecté 2,1%
            "ca3_lb": 200,  # base autoliq import 20%
            "ca3_lc": 40,  # montant autoliq import 20%
            "ca3_ld": 110,  # base autoliq import 10%
            "ca3_le": 11,  # montant autoliq import 10%
            "ca3_lh": 500,  # base autoliq import 5.5%
            "ca3_lj": 28,  # montant autoliq import 5.5%
            "ca3_lk": 2000,  # base autoliq import 2,1%
            "ca3_ll": 42,  # montant autoliq import 2,1%
            "ca3_mg": 100,  # base droits d'auteur
            "ca3_md": 9,  # montant droits d'auteur
            "ca3_gh": 1980,  # Total TVA collectée
            "ca3_gj": 141,  # dont TVA sur acquisitions intracom
            "ca3_gk": 891,  # dont TVA à Monaco
            ######
            "ca3_ha": 1065,  # TVA déduc immo
            "ca3_hb": 584,  # TVA déduc biens et services
            "ca3_hd": initial_credit_vat,  # report crédit TVA
            "ca3_hg": 1671,  # total VAT deduc
            ######
            "ca3_ka": 309,  # TVA à payer (ligne 16 - 23)
            "ca3_nd": 309,  # TVA nette due (ligne TD - X5)
            "ca3_ke": 309,  # Total à payer
        }
        move_result = {
            "445711": 7.5,
            "445712": 1,
            "445713": 981.25,
            "445714": 441,
            "445620": -1065,
            "445660": -34.6,
            "445201": 40,
            "445202": 22,
            "445203": 110,
            "445204": 46.2,
            "445662": -218.2,
            "445301": 60,
            "445302": 31,
            "445303": 165,
            "445304": 65.1,
            "445663": -321.1,
            "445719": 9.2,
            "445669": -10,
            "445510": box_result["ca3_ke"] * -1,
            "445670": initial_credit_vat * -1,
        }
        self._check_vat_return_result(vat_return, box_result, move_result)
        vat_return.print_ca3()
        vat_return.auto2sent_manual()
        self.assertEqual(vat_return.state, "sent")
        self.assertTrue(vat_return.sent_datetime)
        vat_return.sent2posted()
        self.assertEqual(vat_return.state, "posted")
        self._check_vat_return_result(vat_return, box_result, move_result)
        speedy = vat_return._prepare_speedy()
        acc2bal = {
            "445711": -38.5,  # 20%
            "445712": -27,  # 10%
            "445713": -283.75,  # 5,5%
            "445714": -147,  # 2,1 %
            "445715": 0,  # 8,5%
        }
        for acc_code, expected_bal in acc2bal.items():
            acc = aao.search(
                [("code", "=", acc_code), ("company_id", "=", company.id)], limit=1
            )
            self.assertTrue(acc)
            real_bal = acc._fr_vat_get_balance("base_domain_end", speedy)
            self.assertFalse(currency.compare_amounts(real_bal, expected_bal))
        must_be_reconciled = ["445620"]
        for line in vat_return.move_id.line_ids:
            if line.account_id.code in must_be_reconciled:
                self.assertTrue(line.full_reconcile_id)

    def test_vat_return_on_invoice_negative(self):
        company = self.on_invoice_company
        initial_credit_vat = 44
        company._test_create_move_init_vat_credit(
            initial_credit_vat, self.before_start_date
        )
        product_dict = company._test_prepare_product_dict()
        partner_dict = company._test_prepare_partner_dict()
        company._test_create_invoice_with_payment(
            "out_invoice",
            self.start_date,
            partner_dict["france"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 200},
                {"product_id": product_dict["product"][100].id, "price_unit": 100},
            ],
            {},
        )
        company._test_create_invoice_with_payment(
            "out_refund",
            self.start_date,
            partner_dict["france"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 400},
                {"product_id": product_dict["product"][100].id, "price_unit": 200},
            ],
            {},
        )
        company._test_create_invoice_with_payment(
            "out_refund",
            self.start_date,
            partner_dict["extracom"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 300},
                {"product_id": product_dict["product"][100].id, "price_unit": 350},
            ],
            {},
        )
        company._test_create_invoice_with_payment(
            "out_refund",
            self.start_date,
            partner_dict["intracom_b2b"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 10},
            ],
            {},
        )

        company._test_create_invoice_with_payment(
            "in_refund",
            self.start_date,
            partner_dict["france"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 100},
                {"product_id": product_dict["product"][100].id, "price_unit": 10},
            ],
            {},
        )
        company._test_create_invoice_with_payment(
            "in_refund",
            self.start_date,
            partner_dict["france_vendor_vat_on_payment"],
            [{"product_id": product_dict["asset"][55].id, "price_unit": 1000}],
            {self.start_date: "residual"},
        )
        lfavro = self.env["l10n.fr.account.vat.return"]
        vat_return = lfavro.create(
            {
                "company_id": company.id,
                "start_date": self.start_date,
                "vat_periodicity": "1",
            }
        )
        vat_return.manual2auto()
        box_result = {
            "ca3_de": 660,  # F8
            "ca3_ce": 300,  # B5 regul
            "ca3_gg": 76,  # 15 TVA antérieurement déduite à reverser
            "ca3_gh": 76,  # Total TVA collectée
            "ca3_hc": 50,  # Autre TVA à déduire
            "ca3_hh": 50,  # dont regul TVA collectée
            "ca3_hd": initial_credit_vat,  # report crédit TVA
            "ca3_hg": 50 + initial_credit_vat,  # total VAT deduc
            ######
            "ca3_ja": initial_credit_vat - 76 + 50,  # Crédit TVA
            "ca3_jc": initial_credit_vat - 76 + 50,  # Crédit TVA
        }
        move_result = {
            "445711": -40,
            "445712": -10,
            "445660": 21,
            "445620": 55,
            "445670": box_result["ca3_jc"] - box_result["ca3_hd"],
        }
        self._check_vat_return_result(vat_return, box_result, move_result)
        # Test that if box 15 has bad accounting method, the error is catched
        vat_return.back_to_manual()
        self.env.ref("l10n_fr_account_vat_return.ca3_gg").write(
            {"accounting_method": "debit"}
        )
        with self.assertRaises(UserError):
            vat_return.manual2auto()

    def test_vat_return_on_invoice_with_adjustment(self):
        company = self.on_invoice_company
        product_dict = company._test_prepare_product_dict()
        partner_dict = company._test_prepare_partner_dict()
        company._test_create_invoice_with_payment(
            "out_invoice",
            self.start_date,
            partner_dict["france"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 100.4},
                {"product_id": product_dict["product"][55].id, "price_unit": 500.3},
            ],
            {},
        )
        lfavro = self.env["l10n.fr.account.vat.return"]
        vat_return = lfavro.create(
            {
                "company_id": company.id,
                "start_date": self.start_date,
                "vat_periodicity": "1",
            }
        )
        vat_return.manual2auto()
        adj_log_line = self.env["l10n.fr.account.vat.return.line.log"].search(
            [
                ("parent_parent_id", "=", vat_return.id),
                ("compute_type", "=", "adjustment"),
                ("amount", "=", -1),
            ]
        )
        self.assertEqual(len(adj_log_line), 1)
        adj_log_line.parent_id.box_id = self.env["l10n.fr.account.vat.box"].search(
            [("meaning_id", "=", "taxed_op_france")]
        )

    def test_vat_return_btp_subcontracting(self):
        aao = self.env["account.account"]
        company = self.on_payment_company
        currency = company.currency_id
        initial_credit_vat = 22
        company._test_create_move_init_vat_credit(
            initial_credit_vat, self.before_start_date
        )
        company._test_create_invoice_btp_subcontracting_data(self.start_date)

        vat_return = self.env["l10n.fr.account.vat.return"].create(
            {
                "company_id": company.id,
                "start_date": self.start_date,
                "vat_periodicity": "1",
            }
        )

        self.assertEqual(vat_return.end_date, self.end_date)
        self.assertEqual(vat_return.state, "manual")
        vat_return.manual2auto()
        self.assertEqual(vat_return.state, "auto")
        box_result = {
            "ca3_cb": 1160,  # A2 Autres opérations imposables
            "ca3_db": 1890,  # E2 Autres opérations non imposables
            ######
            "ca3_fp": 560,  # base 20%
            "ca3_gp": 112,  # montant collecté 20%
            "ca3_fr": 370,  # base 10%
            "ca3_gr": 37,  # montant collecté 10%
            "ca3_fb": 230,  # base 5,5%
            "ca3_gb": 13,  # montant collecté 5,5%
            "ca3_gh": 162,  # Total TVA collectée
            ######
            "ca3_hb": 162,  # TVA déduc biens et services
            "ca3_hd": initial_credit_vat,  # report crédit TVA
            "ca3_hg": 162 + initial_credit_vat,  # total VAT deduc
            ######
            "ca3_ja": initial_credit_vat,  # Crédit de TVA
            "ca3_jc": initial_credit_vat,  # Crédit TVA à reporter
        }
        move_result = {
            "445401": 112,
            "445402": 37,
            "445403": 12.65,
            "445664": -161.65,
        }
        self._check_vat_return_result(vat_return, box_result, move_result)
        vat_return.print_ca3()
        vat_return.auto2sent_manual()
        self.assertEqual(vat_return.state, "sent")
        vat_return.sent2posted()
        self.assertEqual(vat_return.state, "posted")
        self._check_vat_return_result(vat_return, box_result, move_result)
        aao = self.env["account.account"]
        speedy = vat_return._prepare_speedy()
        acc2bal = {
            "445711": 0,  # 20%
            "445712": 0,  # 10%
            "445713": 0,  # 5,5%
            "445401": 0,
            "445402": 0,
            "445403": 0,
            "445664": 0,
        }
        for acc_code, expected_bal in acc2bal.items():
            acc = aao.search(
                [("code", "=", acc_code), ("company_id", "=", company.id)], limit=1
            )
            self.assertTrue(acc)
            real_bal = acc._fr_vat_get_balance("base_domain_end", speedy)
            self.assertFalse(currency.compare_amounts(real_bal, expected_bal))
        must_be_reconciled = ["445401", "445402", "445403", "445664"]
        for line in vat_return.move_id.line_ids:
            if line.account_id.code in must_be_reconciled:
                self.assertTrue(line.full_reconcile_id)
