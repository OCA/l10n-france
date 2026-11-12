# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAccount(models.Model):
    _inherit = "account.account"

    def _fr_vat_get_balance(self, domain_key, speedy):
        amlo = self.env["account.move.line"]
        rg_res = amlo._read_group(
            speedy[domain_key] + [("account_id", "=", self.id)],
            aggregates=["balance:sum"],
        )
        balance = rg_res and rg_res[0][0] or 0
        balance = speedy["currency"].round(balance)
        return balance
