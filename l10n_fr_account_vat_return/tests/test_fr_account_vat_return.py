# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from collections import defaultdict
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestFrAccountVatReturn(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env["res.company"]._test_fr_vat_create_company(
            company_name="XXX FR Company VAT", fr_vat_exigibility="on_invoice"
        )
        self.currency = self.company.currency_id
        self.today = datetime.now().date()
        self.start_date = self.today + relativedelta(months=-1, day=1)
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
            # print("box.name=%s box_xmlid=%s", box.name, box_xmlid)
            real_valuebox = box2value.pop((box.form_code, box.edi_code))
            self.assertEqual(real_valuebox, expected_value)
        self.assertFalse(box2value)

    def _move_to_dict(self, vat_return):
        assert vat_return.move_id
        move_dict = defaultdict(float)
        for line in vat_return.move_id.line_ids:
            move_dict[line.account_id.code] += line.balance
        self.assertEqual(
            self.currency.compare_amounts(move_dict.get("758000", 0) * -1, 1), -1
        )
        self.assertEqual(
            self.currency.compare_amounts(move_dict.get("658000", 0), 1), -1
        )
        return move_dict

    def test_vat_return(self):
        self.company._test_create_move_init_vat_credit(333, self.start_date)
        self.company._test_create_invoice_data(self.start_date)
        lfavro = self.env["l10n.fr.account.vat.return"]
        vat_return = lfavro.create(
            {
                "company_id": self.company.id,
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
                "company_id": self.company.id,
                "user_type_id": self.env.ref("account.data_account_type_expenses").id,
            }
        )
        self.env.ref("l10n_fr_account_vat_return.a_kj").with_company(
            self.company.id
        ).write({"account_id": manual_account_id})
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
            "ca3_ca": 1810,  # A
            "ca3_kh": 200,  # A3 HA intracom services
            "ca3_cc": 500,  # B2 HA intracom products
            "ca3_cg": 2000,  # B4 HA extracom
            "ca3_da": 1300,  # E1 Extracom
            "ca3_db": 40,  # E2 Autres opérations non imposables
            "ca3_dc": 1250,  # F2
            ######
            "ca3_fp": 3710,  # base 20%
            "ca3_gp": 742,  # montant collecté 20%
            "ca3_fr": 500,  # base 10%
            "ca3_gr": 50,  # montant collecté 10%
            "ca3_fb": 100,  # base 5,5%
            "ca3_gb": 6,  # montant collecté 5,5%
            "a_bb": 200,  # base 2,1%
            "a_cb": 4,  # montant collecté 2,1%
            "a_bn": 200,  # total base annexe
            "a_cn": 4,  # montant collecté annexe
            "ca3_fd": 200,  # report base annexe
            "ca3_gd": 4,  # report collecté annexe
            "ca3_gh": 802,  # Total TVA collectée
            "ca3_gj": 100,  # dont TVA sur acquisitions intracom
            "ca3_gk": 2,  # dont TVA à Monaco
            ######
            "ca3_ha": 1065,  # TVA déduc immo
            "ca3_hb": 635,  # TVA déduc biens et services
            "ca3_hd": 333,  # report crédit TVA
            "ca3_hg": 2033,  # total VAT deduc
            ######
            "a_jb": 134,
            "a_mk": 1000,
            "a_kj": 52,
            "a_hb": 186,
            #                'ca3_ka': 0,   # TVA à payer (ligne 16 - 23)
            "ca3_kb": 186,  # Report taxes annexes
            "ca3_ke": 186,  # Total à payer
            "ca3_ja": 1231,  # credit TVA (ligne 23 - 16)
            "ca3_jc": 1231,  # crédit à reporter
        }
        self._check_vat_return_result(vat_return, expected_res)
        self.assertTrue(vat_return.move_id)
        self.assertEqual(vat_return.move_id.state, "draft")
        self.assertEqual(vat_return.move_id.date, vat_return.end_date)
        self.assertEqual(vat_return.move_id.journal_id, self.company.fr_vat_journal_id)
        move_dict = self._move_to_dict(vat_return)
        self.assertFalse(
            self.currency.compare_amounts(
                move_dict["447000"], expected_res["ca3_kb"] * -1
            )
        )
        self.assertFalse(
            self.currency.compare_amounts(
                move_dict["445670"], expected_res["ca3_jc"] - expected_res["ca3_hd"]
            )
        )
        self.assertFalse(
            self.currency.compare_amounts(move_dict["635820"], expected_res["a_kj"])
        )
        self.assertFalse(
            self.currency.compare_amounts(move_dict["635800"], expected_res["a_jb"])
        )

        # Test reimbursement
        self.assertTrue(vat_return.reimbursement_show_button)
        reimbursement_type = "first"
        reimb_wiz = self.env["l10n.fr.account.vat.return.reimbursement"].create(
            {
                "return_id": vat_return.id,
                "amount": 1000,
                "reimbursement_type": reimbursement_type,
                "first_creation_date": self.first_creation_date,
            }
        )
        reimb_wiz.validate()
        reimb_expected_res = dict(expected_res)
        reimb_expected_res.update(
            {
                "ca3_jb": 1000,
                "ca3_jc": 231,
            }
        )
        self._check_vat_return_result(vat_return, reimb_expected_res)
        self.assertEqual(vat_return.reimbursement_type, reimbursement_type)
        self.assertEqual(
            vat_return.reimbursement_first_creation_date, self.first_creation_date
        )
        move_dict = self._move_to_dict(vat_return)
        self.assertFalse(self.currency.compare_amounts(move_dict["445830"], 1000))
        self.assertFalse(self.currency.compare_amounts(move_dict["445670"], -102))
        vat_return.remove_credit_vat_reimbursement()
        self._check_vat_return_result(vat_return, expected_res)
        self.assertFalse(vat_return.reimbursement_type)
        self.assertFalse(vat_return.reimbursement_first_creation_date)
        vat_return.print_ca3()
        vat_return.auto2sent()
        self.assertEqual(vat_return.state, "sent")
        vat_return.sent2posted()
        self.assertEqual(vat_return.state, "posted")
        self.assertEqual(vat_return.move_id.state, "posted")
        aao = self.env["account.account"]
        speedy = vat_return._prepare_speedy()
        for acc_code in ("445711", "445712", "445713", "445714", "445715"):
            acc = aao.browse(acc_code)
            balance = acc._fr_vat_get_balance("base_domain_end", speedy)
            self.assertTrue(self.currency.is_zero(balance))
