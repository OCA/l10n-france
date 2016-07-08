# -*- coding: utf-8 -*-
##############################################################################
#
#    account_bank_statement_import_fr_cfonb module for Odoo
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

import logging
from datetime import datetime
from openerp import models, fields, api, _
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    _excluded_accounts = []

    def _parse_cfonb_amount(self, amount_str, nb_of_dec):
        """Taken from the cfonb lib"""
        amount_str = amount_str[:-nb_of_dec] + '.' + amount_str[-nb_of_dec:]
        # translate the last char and set the sign
        credit_trans = {
            'A': '1', 'B': '2', 'C': '3', 'D': '4', 'E': '5',
            'F': '6', 'G': '7', 'H': '8', 'I': '9', '{': '0'}
        debit_trans = {
            'J': '1', 'K': '2', 'L': '3', 'M': '4', 'N': '5',
            'O': '6', 'P': '7', 'Q': '8', 'R': '9', '}': '0'}
        assert (
            amount_str[-1] in debit_trans or amount_str[-1] in credit_trans),\
            'Invalid amount in CFONB file'
        if amount_str[-1] in debit_trans:
            amount_num = float(
                '-' + amount_str[:-1] + debit_trans[amount_str[-1]])
        elif amount_str[-1] in credit_trans:
            amount_num = float(amount_str[:-1] + credit_trans[amount_str[-1]])
        return amount_num

    @api.model
    def _check_cfonb(self, data_file):
        return data_file.strip().startswith('01')

    @api.model
    def _parse_file(self, data_file):
        """ Import a file in French CFONB format"""
        cfonb = self._check_cfonb(data_file)
        if not cfonb:
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)
        transactions = []
        if not data_file.splitlines():
            raise UserError(
                _('The file is empty.'))
        i = 0
        bank_code = guichet_code = account_number = currency_code = False
        decimals = start_balance = False
        start_balance = end_balance = start_date_str = end_date_str = False
        vals_line = False
        for line in data_file.splitlines():
            i += 1
            _logger.debug("Line %d: %s" % (i, line))
            if not line:
                continue
            if len(line) != 120:
                raise UserError(
                    _('Line %d is %d caracters long. All lines of a '
                        'CFONB bank statement file must be 120 caracters '
                        'long.')
                    % (i, len(line)))
            line_bank_code = line[2:7]
            line_guichet_code = line[11:16]
            line_account_number = line[21:32]
            line_currency_code = line[16:19]
            rec_type = line[0:2]
            decimals = int(line[19:20])
            date_cfonb_str = line[34:40]
            date_dt = False
            date_str = False
            if line_account_number in self._excluded_accounts:
                continue
            if date_cfonb_str != '      ':
                date_dt = datetime.strptime(date_cfonb_str, '%d%m%y')
                date_str = fields.Date.to_string(date_dt)
            assert decimals == 2, 'We use 2 decimals in France!'

            if i == 1:
                bank_code = line_bank_code
                guichet_code = line_guichet_code
                currency_code = line_currency_code
                account_number = line_account_number
                if rec_type != '01':
                    raise UserError(
                        _("The 2 first letters of the first line are '%s'. "
                            "A CFONB file should start with '01'")
                        % rec_type)
                start_balance = self._parse_cfonb_amount(
                    line[90:104], decimals)
                start_date_str = date_str

            if (
                    bank_code != line_bank_code or
                    guichet_code != line_guichet_code or
                    currency_code != line_currency_code or
                    account_number != line_account_number):
                raise UserError(
                    _('Only single-account files and single-currency '
                        'files are supported for the moment. It is not '
                        'the case starting from line %d.') % i)

            if rec_type in ('04', '01', '07') and vals_line:
                # I save the previous line
                # This trick is needed for the 05 lines
                transactions.append(vals_line)
                vals_line = False
            if rec_type == '07':
                end_date_str = date_str
                end_balance = self._parse_cfonb_amount(line[90:104], decimals)
            elif rec_type == '04':
                bank_account_id = partner_id = False
                amount = self._parse_cfonb_amount(line[90:104], decimals)
                ref = line[81:88].strip()  # This is not unique
                name = line[48:79].strip()
                vals_line = {
                    'date': date_str,
                    'name': name,
                    'ref': ref,
                    'unique_import_id':
                    '%s-%s-%.2f-%s' % (date_str, ref, amount, name),
                    'amount': amount,
                    'partner_id': partner_id,
                    'bank_account_id': bank_account_id,
                }
            elif rec_type == '05':
                assert vals_line, 'vals_line should have a value !'
                vals_line['name'] += ' %s' % line[48:79].strip()

        vals_bank_statement = {
            'name': _('Account %s %s > %s') % (
                account_number, start_date_str, end_date_str),
            'balance_start': start_balance,
            'balance_end_real': end_balance,
            'transactions': transactions,
            }
        return currency_code, account_number, [vals_bank_statement]
