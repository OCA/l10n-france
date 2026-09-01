# Copyright 2025  Akretion (https://www.akretion.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import base64

from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_path


class TestMercanetImport(TransactionCase):
    def setUp(self):
        super().setUp()
        self.receivable_account_id = self.env["account.account"].create(
            {
                "name": "Customer account",
                "code": "411101",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        self.bank_mercanet_account = self.env["account.account"].create(
            {
                "name": "Adyen bank account",
                "code": "511007",
                "account_type": "income",
            }
        )
        self.mercanet_journal = self.env["account.journal"].create(
            {
                "name": "Mercanet Payments",
                "type": "bank",
                "code": "ADY",
                "default_account_id": self.bank_mercanet_account.id,
                "used_for_import": True,
                "import_type": "mercanet_cb_csvparser",
                "receivable_account_id": self.receivable_account_id.id,
            }
        )

    def _get_import_wizard(self, filename):
        f_path = file_path(f"account_move_mercanet_import/tests/files/{filename}")
        data = base64.b64encode(open(f_path, "rb").read())
        wizard = self.env["credit.statement.import"].create(
            {
                "journal_id": self.mercanet_journal.id,
                "input_statement": data,
                "receivable_account_id": self.receivable_account_id.id,
                "file_name": filename,
            }
        )
        return wizard

    def test_import_mercanet_file(self):
        wizard = self._get_import_wizard("mercanet_operations.xls")
        wizard.import_statement()
        move = self.env["account.move"].search(
            [("journal_id", "=", self.mercanet_journal.id)]
        )
        self.assertEqual(len(move), 1)
        self.assertEqual(len(move.line_ids), 3)
        payment_aml1 = move.line_ids.filtered(lambda line: line.name == "ref1")
        self.assertAlmostEqual(payment_aml1.credit, 19.99)
        payment_aml2 = move.line_ids.filtered(lambda line: line.name == "ref2")
        self.assertAlmostEqual(payment_aml2.credit, 40.00)
        counterpart_aml = move.line_ids.filtered(
            lambda line: line.account_id == self.bank_mercanet_account
        )
        self.assertEqual(counterpart_aml.debit, 59.99)
