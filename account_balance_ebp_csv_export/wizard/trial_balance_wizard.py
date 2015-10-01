# -*- coding: utf-8 -*-
##############################################################################
#
#    Account Balance EBP CSV export module for Odoo
#    Copyright (C) 2014-2015 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import orm


class AccountTrialBalanceWizard(orm.TransientModel):
    _inherit = "trial.balance.webkit"

    def _print_report(self, cursor, uid, ids, data, context=None):
        if context is None:
            context = {}
        res = super(AccountTrialBalanceWizard, self)._print_report(
            cursor, uid, ids, data, context=context)
        if context.get('export_type') == 'ebp-csv':
            res['report_name'] = 'account.report.trial.balance.ebp.csv'
        return res
