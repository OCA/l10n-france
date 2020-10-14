# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def process_reconciliation(
        self,
        counterpart_aml_dicts=None,
        payment_aml_rec=None,
        new_aml_dicts=None,
    ):
        if payment_aml_rec:
            payment_aml_rec = payment_aml_rec.with_context(no_post=True)

        return super(
            AccountBankStatementLine, self.with_context(no_post=True)
        ).process_reconciliation(
            counterpart_aml_dicts, payment_aml_rec, new_aml_dicts
        )
