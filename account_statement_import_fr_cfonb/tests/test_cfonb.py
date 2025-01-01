# Copyright 2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64

from odoo.tests.common import TransactionCase
from odoo.tools import file_open


class TestAccountStatementImportFrCfonb(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.eur_cur = cls.env.ref("base.EUR")
        cls.wiz_model = cls.env["account.statement.import"]
        cls.st_model = cls.env["account.bank.statement"]
        partner_bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": "01234567890",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
            }
        )
        cls.bank_journal = cls.env["account.journal"].create(
            {
                "name": "CFONB Test journal",
                "code": "CFOZZ",
                "type": "bank",
                "bank_account_id": partner_bank.id,
                "currency_id": cls.eur_cur.id,
            }
        )

    def cfonb_file_generic(self, filename):
        path = f"account_statement_import_fr_cfonb/tests/samples/{filename}"
        with file_open(path, "rb") as cfonb_file:
            cfonb_bin = cfonb_file.read()
            wizard = self.wiz_model.create(
                {
                    "statement_file": base64.b64encode(cfonb_bin),
                    "statement_filename": filename,
                }
            )
            res = wizard.import_file_button()
            self.assertEqual(res["res_model"], "account.bank.statement")
            st_id = res["domain"][0][2][0]
            stmt = self.st_model.browse(st_id)
            self.assertFalse(
                self.eur_cur.compare_amounts(stmt.balance_start, 1017311.89)
            )
            self.assertFalse(
                self.eur_cur.compare_amounts(stmt.balance_end_real, 1031585.79)
            )
            self.assertEqual(len(stmt.line_ids), 13)
            self.assertEqual(stmt.journal_id.id, self.bank_journal.id)
            for line in stmt.line_ids:
                self.assertEqual(line.date.strftime("%Y%m%d"), "20240113")

    def test_cfonb_file_classic(self):
        self.cfonb_file_generic("cfonb_classic.cfo")

    def test_cfonb_file_no_carriage_return(self):
        self.cfonb_file_generic("cfonb_no_carriage_return.cfo")
