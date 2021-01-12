# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class TrialBalanceEBP(models.AbstractModel):
    _name = "report.account_balance_ebp_csv_export.trial_balance_ebp"
    _description = "EBP CSV Trial Balance"

    def _get_report_values(self, docids, data):
        model = self.env["report.account_financial_report.trial_balance"]
        return model._get_report_values(docids, data)
