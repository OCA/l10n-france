# -*- coding: utf-8 -*-
# © 2016-2018 Akretion France
# @author: Sébastien Beau <sebastien.beau@akretion.com>
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class TrialBalanceReportWizard(models.TransientModel):
    _inherit = 'trial.balance.report.wizard'

    def button_export_ebp_csv(self):
        rtbqo = self.env['report_trial_balance_qweb']
        report = rtbqo.create(self._prepare_report_trial_balance())
        report.compute_data_for_report()
        action = self.env['report'].get_action(
            docids=report.ids, report_name='account_balance_ebp_csv_export.'
            'report_trial_balance_ebp_csv')
        return action
