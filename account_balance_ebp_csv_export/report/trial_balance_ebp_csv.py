# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright Camptocamp SA 2011
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


from openerp.report import report_sxw
from openerp import pooler
from openerp.addons.account_financial_report_webkit.report.\
    common_balance_reports import CommonBalanceReportHeaderWebkit


class Parser(report_sxw.rml_parse, CommonBalanceReportHeaderWebkit):

    def __init__(self, cursor, uid, name, context):
        super(Parser, self).__init__(cursor, uid, name, context=context)
        self.pool = pooler.get_pool(self.cr.dbname)
        self.cursor = self.cr
        self.localcontext.update({
            'cr': cursor,
            'uid': uid,
            'display_account': self._get_display_account,
            'display_account_raw': self._get_display_account_raw,
            'filter_form': self._get_filter,
            'target_move': self._get_target_move,
            'display_target_move': self._get_display_target_move,
            'accounts': self._get_accounts_br,
        })

    def set_context(self, objects, data, ids, report_type=None):
        objects, new_ids, context_report_values = self.compute_balance_data(
            data)
        self.localcontext.update(context_report_values)
        return super(Parser, self).set_context(
            objects, data, new_ids, report_type=report_type)
