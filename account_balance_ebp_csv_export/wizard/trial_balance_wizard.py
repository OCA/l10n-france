# -*- coding: utf-8 -*-
# © 2016 Akretion France
# @author: Sébastien Beau <sebastien.beau@akretion.com>
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, api
from openerp.report import interface
from openerp.addons.account_financial_report_webkit.report.\
    trial_balance import TrialBalanceWebkit
import unicodecsv

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class ReportEBP(interface.report_int):

    def create(self, cr, uid, ids, data, context=None):
        def f2s(value):
            return '%.2f' % value

        # Get objects and context from Webkit Parser
        parser = TrialBalanceWebkit(
            cr, uid, 'ebp.parser', context=context)
        objects, new_ids, ctx_val =\
            parser.compute_balance_data(data)

        # Init file and write header
        f = StringIO()
        w = unicodecsv.writer(
            f, delimiter=',', encoding='utf-8',
            quoting=unicodecsv.QUOTE_MINIMAL)

        header = [
            "Compte.Numero",
            "Compte.Intitule",
            "Balance.SldCptNDebit",
            "Balance.SldCptNCredit",
            "Balance.SldCptNSoldeD",
            "Balance.SldCptNSoldeC",
            ]
        w.writerow(header)
        # Write row
        for current_account in objects:
            if ctx_val['to_display_accounts'].get(current_account.id) \
                    and current_account.type != 'view':
                bal = ctx_val['balance_accounts'][current_account.id]
                if bal >= 0:
                    bal_debit = bal
                    bal_credit = 0
                else:
                    bal_credit = -bal
                    bal_debit = 0

                w.writerow([
                    current_account.code,
                    current_account.name,
                    f2s(ctx_val['debit_accounts'][current_account.id]),
                    f2s(ctx_val['credit_accounts'][current_account.id]),
                    f2s(bal_debit),
                    f2s(bal_credit),
                    ])
        # Read and return File
        f.seek(0)
        data = f.read()
        return (data, 'csv')

ReportEBP('report.trial.balance.ebp')


class AccountTrialBalanceWizard(models.TransientModel):
    _inherit = "trial.balance.webkit"

    @api.multi
    def _print_report(self, data):
        res = super(AccountTrialBalanceWizard, self)._print_report(
            data)
        if self.env.context.get('export_type') == 'ebp-csv':
            res['report_name'] = 'trial.balance.ebp'
        return res
