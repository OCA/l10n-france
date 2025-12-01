# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo.modules.module import get_resource_path
from odoo.tests.common import TransactionCase


class TestMoneticoImportCardRemitance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.receivable_account_id = cls.env["account.account"].create(
            {
                "name": "Customer account",
                "code": "411101",
                "account_type": "asset_receivable",
            }
        )
        cls.bank_monetico_account = cls.env["account.account"].create(
            {
                "name": "Adyen bank account",
                "code": "511007",
                "account_type": "asset_cash",
            }
        )
        cls.monetico_journal = cls.env["account.journal"].create(
            {
                "name": "Monetico Payments",
                "type": "bank",
                "code": "ADY",
                "default_account_id": cls.bank_monetico_account.id,
                "used_for_import": True,
                "import_type": "monetico_cb_csvparser",
                "receivable_account_id": cls.receivable_account_id.id,
            }
        )

    def _get_import_wizard(self, filename):
        file_path = get_resource_path(
            "account_move_monetico_import", "tests/files/", filename
        )
        data = base64.b64encode(open(file_path, "rb").read())
        wizard = self.env["credit.statement.import"].create(
            {
                "journal_id": self.monetico_journal.id,
                "input_statement": data,
                "receivable_account_id": self.receivable_account_id.id,
                "file_name": filename,
            }
        )
        return wizard

    def test_import_csv_file(self):
        wizard = self._get_import_wizard("monetico.csv")
        wizard.import_statement()
        move = self.env["account.move"].search(
            [("journal_id", "=", self.monetico_journal.id)]
        )
        self.assertEqual(len(move), 1)
        self.assertEqual(len(move.line_ids), 3)
        payment_aml1 = move.line_ids.filtered(lambda line: line.name == "ref1")
        self.assertAlmostEqual(payment_aml1.credit, 2197.89)
        payment_aml2 = move.line_ids.filtered(lambda line: line.name == "ref2")
        self.assertAlmostEqual(refund_aml1.credit, 1577.54)
        counterpart_aml = move.line_ids.filtered(
            lambda line: line.account_id == self.bank_monetico_account
        )
        self.assertEqual(counterpart_aml.debit, 3775.43)
