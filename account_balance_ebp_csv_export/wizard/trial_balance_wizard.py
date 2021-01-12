# Copyright 2016-2021 Akretion France (http://www.akretion.com/)
# @author: Sébastien Beau <sebastien.beau@akretion.com>
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class TrialBalanceReportWizard(models.TransientModel):
    _inherit = "trial.balance.report.wizard"

    def button_export_ebp_csv(self):
        data = self._prepare_report_trial_balance()
        ir_report = self.env.ref(
            "account_balance_ebp_csv_export.action_report_trial_balance_ebp"
        )
        action = ir_report.report_action(self, data=data)
        return action
