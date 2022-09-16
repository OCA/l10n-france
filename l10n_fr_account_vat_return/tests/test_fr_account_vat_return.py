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
    def setUp(self):
        super().setUp()
        self.today = datetime.now().date()
        self.start_date = self.today + relativedelta(months=-1, day=1)
        self.before_start_date = self.start_date + relativedelta(days=-1)
        self.end_date = self.start_date + relativedelta(day=31)
        self.first_creation_date = fields.Date.from_string("2022-01-01")

    def _check_vat_return_result(self, vat_return, result):
        box2value = {}
        for line in vat_return.line_ids.filtered(
            lambda x: not x.box_display_type and x.box_edi_type == "MOA"
        ):
            box2value[(line.box_form_code, line.box_edi_code)] = line.value
        for box_xmlid, expected_value in result.items():
            box = self.env.ref("l10n_fr_account_vat_return.%s" % box_xmlid)
            real_valuebox = box2value.pop((box.form_code, box.edi_code))
            self.assertEqual(real_valuebox, expected_value)
        self.assertFalse(box2value)

    def _move_to_dict(self, move):
        assert move
        currency = move.company_id.currency_id
        move_dict = defaultdict(float)
        for line in move.line_ids:
            move_dict[line.account_id.code] += line.balance
        self.assertEqual(
            currency.compare_amounts(move_dict.get("758000", 0) * -1, 1), -1
        )
        self.assertEqual(currency.compare_amounts(move_dict.get("658000", 0), 1), -1)
        return move_dict

    def test_vat_return_on_invoice(self):
        res = self.env["res.company"]._test_fr_vat_create_company(
            company_name="FR Company VAT on_invoice", fr_vat_exigibility="on_invoice"
        )
        company, intracom_purchase_tax_dict = res
        currency = company.currency_id
        initial_credit_vat = 3333
        company._test_create_move_init_vat_credit(
            initial_credit_vat, self.before_start_date
        )
        company._test_create_invoice_data(self.start_date, intracom_purchase_tax_dict)
        vat_return = self.env["l10n.fr.account.vat.return"].create(
            {
                "company_id": company.id,
                "start_date": self.start_date,
                "vat_periodicity": "1",
            }
        )
        self.assertEqual(vat_return.end_date, self.end_date)
        self.assertEqual(vat_return.state, "manual")
        # Create a manual line redevance TV
        self.env["l10n.fr.account.vat.return.line"].create(
            {
                "box_id": self.env.ref("l10n_fr_account_vat_return.a_jb").id,
                "value_manual_int": 134,
                "parent_id": vat_return.id,
            }
        )
        # Create another manual line with a rate
        manual_account_id = self.env["account.account"].create(
            {
                "code": "635820",
                "name": "Taxe sur la diffusion de contenus audiovisuels",
                "company_id": company.id,
                "user_type_id": self.env.ref("account.data_account_type_expenses").id,
            }
        )
        self.env.ref("l10n_fr_account_vat_return.a_kj").with_company(company.id).write(
            {"account_id": manual_account_id}
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
        expected_res = {
            "ca3_ca": 51510,  # A
            "ca3_kh": 2210,  # A3 HA intracom services
            "ca3_cc": 2410,  # B2 HA intracom products
            "ca3_cg": 6710,  # B4 HA extracom
            "ca3_da": 750,  # E1 Extracom
            "ca3_db": 1400,  # E2 Autres opérations non imposables
            "ca3_dc": 150,  # F2 livraisons intracom
            ######
            "ca3_fp": 730,  # base 20%
            "ca3_gp": 146,  # montant collecté 20%
            "ca3_fr": 810,  # base 10%
            "ca3_gr": 81,  # montant collecté 10%
            "ca3_fb": 28000,  # base 5,5%
            "ca3_gb": 1540,  # montant collecté 5,5%
            "a_bb": 33300,  # base 2,1%
            "a_cb": 699,  # montant collecté 2,1%
            "a_bn": 33300,  # total base annexe
            "a_cn": 699,  # montant collecté annexe
            "ca3_fd": 33300,  # report base annexe
            "ca3_gd": 699,  # report collecté annexe
            "ca3_gh": 2466,  # Total TVA collectée
            "ca3_gj": 141,  # dont TVA sur acquisitions intracom
            "ca3_gk": 891,  # dont TVA à Monaco
            ######
            "ca3_ha": 1065,  # TVA déduc immo
            "ca3_hb": 634,  # TVA déduc biens et services
            "ca3_hd": initial_credit_vat,  # report crédit TVA
            "ca3_hg": 5032,  # total VAT deduc
            ######
            "a_jb": 134,
            "a_mk": 1000,
            "a_kj": 52,
            "a_hb": 186,
            "ca3_kb": 186,  # Report taxes annexes
            "ca3_ke": 186,  # Total à payer
            "ca3_ja": 2566,  # credit TVA (ligne 23 - 16)
            "ca3_jc": 2566,  # crédit à reporter
        }
        self._check_vat_return_result(vat_return, expected_res)
        move = vat_return.move_id
        self.assertTrue(move)
        self.assertEqual(move.state, "draft")
        self.assertEqual(move.date, vat_return.end_date)
        self.assertEqual(move.journal_id, company.fr_vat_journal_id)
        move_dict = self._move_to_dict(move)
        self.assertFalse(
            currency.compare_amounts(move_dict["447000"], expected_res["ca3_kb"] * -1)
        )
        self.assertFalse(
            currency.compare_amounts(
                move_dict["445670"], expected_res["ca3_jc"] - expected_res["ca3_hd"]
            )
        )
        self.assertFalse(
            currency.compare_amounts(move_dict["635820"], expected_res["a_kj"])
        )
        self.assertFalse(
            currency.compare_amounts(move_dict["635800"], expected_res["a_jb"])
        )

        # Test reimbursement
        self.assertTrue(vat_return.reimbursement_show_button)
        reimbursement_type = "first"
        reimbursement_amount = 2000
        reimb_wiz = self.env["l10n.fr.account.vat.return.reimbursement"].create(
            {
                "return_id": vat_return.id,
                "amount": reimbursement_amount,
                "reimbursement_type": reimbursement_type,
                "first_creation_date": self.first_creation_date,
            }
        )
        reimb_wiz.validate()
        reimb_expected_res = dict(expected_res)
        reimb_expected_res.update(
            {
                "ca3_jb": reimbursement_amount,
                "ca3_jc": expected_res["ca3_jc"] - reimbursement_amount,
            }
        )
        self._check_vat_return_result(vat_return, reimb_expected_res)
        self.assertEqual(vat_return.reimbursement_type, reimbursement_type)
        self.assertEqual(
            vat_return.reimbursement_first_creation_date, self.first_creation_date
        )
        move = vat_return.move_id
        move_dict = self._move_to_dict(move)
        self.assertFalse(
            currency.compare_amounts(move_dict["445830"], reimbursement_amount)
        )
        # 445670: Do not mix the balance of the move and the balance of the
        # account. The balance of the account must be equal to
        # reimb_expected_res["ca3_jc"]
        self.assertFalse(
            currency.compare_amounts(
                initial_credit_vat + move_dict["445670"], reimb_expected_res["ca3_jc"]
            )
        )
        vat_return.remove_credit_vat_reimbursement()
        move = vat_return.move_id
        self._check_vat_return_result(vat_return, expected_res)
        self.assertFalse(vat_return.reimbursement_type)
        self.assertFalse(vat_return.reimbursement_first_creation_date)
        vat_return.print_ca3()
        with self.assertRaises(UserError):
            vat_return.generate_selenium_file()
        vat_return.auto2sent()
        self.assertEqual(vat_return.state, "sent")
        vat_return.sent2posted()
        self.assertEqual(vat_return.state, "posted")
        self.assertEqual(move.state, "posted")
        aao = self.env["account.account"]
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
        for line in move.line_ids:
            if line.account_id.code in must_be_reconciled:
                self.assertTrue(line.full_reconcile_id)

    def test_vat_return_on_payment(self):
        res = self.env["res.company"]._test_fr_vat_create_company(
            company_name="FR Company VAT on_payment", fr_vat_exigibility="on_payment"
        )
        company, intracom_purchase_tax_dict = res
        currency = company.currency_id
        initial_credit_vat = 22
        company._test_create_move_init_vat_credit(
            initial_credit_vat, self.before_start_date
        )
        company._test_create_invoice_data(
            self.start_date, intracom_purchase_tax_dict, extracom_refund_ratio=2
        )
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
        expected_res = {
            "ca3_ca": 40148,  # A
            "ca3_kh": 2210,  # A3 HA intracom services
            "ca3_cc": 2410,  # B2 HA intracom products
            "ca3_cg": 6710,  # B4 HA extracom
            "ca3_db": 1400,  # E2 Autres opérations non imposables
            "ca3_dc": 150,  # F2 livraisons intracom
            "ca3_de": 1500,  # F8 régularisations
            # => replaces E1 because the extracom amount is negative
            ######
            "ca3_fp": 688,  # base 20%
            "ca3_gp": 138,  # montant collecté 20%
            "ca3_fr": 740,  # base 10%
            "ca3_gr": 74,  # montant collecté 10%
            "ca3_fb": 23750,  # base 5,5%
            "ca3_gb": 1306,  # montant collecté 5,5%
            "a_bb": 26300,  # base 2,1%
            "a_cb": 552,  # montant collecté 2,1%
            "a_bn": 26300,  # total base annexe
            "a_cn": 552,  # montant collecté annexe
            "ca3_fd": 26300,  # report base annexe
            "ca3_gd": 552,  # report collecté annexe
            "ca3_gh": 2070,  # Total TVA collectée
            "ca3_gj": 141,  # dont TVA sur acquisitions intracom
            "ca3_gk": 891,  # dont TVA à Monaco
            ######
            "ca3_ha": 1065,  # TVA déduc immo
            "ca3_hb": 634,  # TVA déduc biens et services
            "ca3_hd": initial_credit_vat,  # report crédit TVA
            "ca3_hg": 1721,  # total VAT deduc
            ######
            "ca3_ka": 349,  # TVA à payer (ligne 16 - 23)
            "ca3_ke": 349,  # Total à payer
        }
        self._check_vat_return_result(vat_return, expected_res)
        move = vat_return.move_id
        self.assertTrue(move)
        self.assertEqual(move.state, "draft")
        self.assertEqual(move.date, vat_return.end_date)
        self.assertEqual(move.journal_id, company.fr_vat_journal_id)
        move_dict = self._move_to_dict(move)
        self.assertFalse(
            currency.compare_amounts(move_dict["445510"], expected_res["ca3_ke"] * -1)
        )
        self.assertFalse(
            currency.compare_amounts(move_dict["445670"], initial_credit_vat * -1)
        )
        vat_return.print_ca3()
        with self.assertRaises(UserError):
            vat_return.generate_selenium_file()
        vat_return.auto2sent()
        self.assertEqual(vat_return.state, "sent")
        vat_return.sent2posted()
        self.assertEqual(vat_return.state, "posted")
        self.assertEqual(move.state, "posted")
        aao = self.env["account.account"]
        speedy = vat_return._prepare_speedy()
        acc2bal = {
            "445711": -8.5,  # 20%
            "445712": -7,  # 10%
            "445713": 0,  # 8,5%
            "445714": -233.75,  # 5,5%
            "445715": -147,  # 2,1 %
        }
        for acc_code, expected_bal in acc2bal.items():
            acc = aao.search(
                [("code", "=", acc_code), ("company_id", "=", company.id)], limit=1
            )
            self.assertTrue(acc)
            real_bal = acc._fr_vat_get_balance("base_domain_end", speedy)
            self.assertFalse(currency.compare_amounts(real_bal, expected_bal))
        must_be_reconciled = ["445620"]
        for line in move.line_ids:
            if line.account_id.code in must_be_reconciled:
                self.assertTrue(line.full_reconcile_id)

    def test_vat_return_on_invoice_negative(self):
        res = self.env["res.company"]._test_fr_vat_create_company(
            company_name="FR Company VAT on_invoice neg",
            fr_vat_exigibility="on_invoice",
        )
        company, intracom_purchase_tax_dict = res
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
        expected_res = {
            "ca3_ce": 300,  # B5 regul
            "ca3_gg": 76,  # 15 TVA antérieurement déduite à reverser
            "ca3_gh": 76,  # Total TVA collectée
            "ca3_hc": 50,  # TVA déduc biens et services
            "ca3_hd": initial_credit_vat,  # report crédit TVA
            "ca3_hg": 50 + initial_credit_vat,  # total VAT deduc
            ######
            "ca3_ja": initial_credit_vat - 76 + 50,  # Crédit TVA
            "ca3_jc": initial_credit_vat - 76 + 50,  # Crédit TVA
        }
        self._check_vat_return_result(vat_return, expected_res)
