# -*- coding: utf-8 -*-
# Copyright 2014-2016 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2018 Florent de Labarre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

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

    def _RIBwithoutkey2IBAN(self, banque, guichet, compte):
        lettres = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        chiffres = '12345678912345678923456789'
        for char in compte:
            if char in lettres:
                achar = char.upper()
                achiffre = chiffres[lettres.find(achar)]
                compte = compte.replace(char, achiffre)
        reste = (89 * int(banque) + 15 * int(guichet) + 3 * int(compte)) % 97
        cle = 97 - reste
        rib = str(banque) + str(guichet) + str(compte) + str(cle)
        tmp_iban = int(''.join(str(int(c, 36)) for c in rib + 'FR00'))
        key = 98 - (tmp_iban % 97)
        return 'FR%.2d%s' % (key, rib)

    @api.model
    def _check_cfonb(self, data_file):
        return data_file.decode('latin1').startswith('01')

    def _get_cfonb_st_name(self, account_number, start_date_str, end_date_str):
        name = _('%s  %s > %s'
                 ) % (account_number, start_date_str, end_date_str)
        return name

    @api.model
    def _parse_file_cfonb(self, data_file):
        """ Import a file in French CFONB format"""

        data_file_split = data_file.decode('latin1').splitlines()

        currency_code = False
        decimals = False
        start_balance = end_balance = False
        start_date_str = end_date_str = False
        vals_line = False
        banks = []
        transactions = []
        data_line = []

        # if one line file
        if len(data_file_split) == 1:
            for start in range(0, len(data_file_split[0]), 120):
                data_line.append(data_file_split[0][start:start + 120])
        else:
            for line in data_file_split:
                data_line.append(line)

        for i, line in enumerate(data_line):
            _logger.debug("Line %d: %s" % (i, line))
            if not line:
                continue
            if len(line) != 120:
                line = line[0:120]
                raise UserError(
                    _('Line %d is %d caracters long. All lines of a '
                        'CFONB bank statement file must be 120 caracters '
                        'long.') % (i, len(line)))
            line_bank_code = line[2:7]
            line_guichet_code = line[11:16]
            line_account_number = line[21:32]
            line_currency_code = line[16:19]
            rec_type = line[0:2]
            decimals = int(line[19:20])
            if decimals != 2:
                raise UserError(_('We use 2 decimals in France!'))
            date_cfonb_str = line[34:40]
            date_dt = False
            date_str = False

            line_iban = self._RIBwithoutkey2IBAN(line_bank_code,
                                                 line_guichet_code,
                                                 line_account_number)

            if date_cfonb_str != '      ':
                date_dt = datetime.strptime(date_cfonb_str, '%d%m%y')
                date_str = fields.Date.to_string(date_dt)

            if rec_type in ('04', '01', '07') and vals_line:
                # I save the previous line
                # This trick is needed for the 05 lines
                transactions.append(vals_line)
                vals_line = False

            if rec_type == '01':
                iban = line_iban
                start_balance = self._parse_cfonb_amount(
                    line[90:104], decimals)
                currency_code = line_currency_code
            elif rec_type == '04':
                if iban != line_iban:
                    raise UserError(
                        _('Error CFONB File, account line is \
                        differente from the last account line %d.') % i)
                amount = self._parse_cfonb_amount(line[90:104], decimals)
                ref = line[81:88].strip()  # This is not unique
                name = line[48:79].strip()
                unique_import_id = '%s-%s-%.2f-%s' % (date_str,
                                                      ref,
                                                      amount,
                                                      name,
                                                      )

                vals_line = {
                    'sequence': i,
                    'date': date_str,
                    'name': name,
                    'ref': ref,
                    'unique_import_id': unique_import_id,
                    'amount': amount,
                }
                if not start_date_str:
                    start_date_str = date_str
                end_date_str = date_str
            elif rec_type == '05':
                if not vals_line:
                    raise UserError(
                        _('Error CFONB File, bad format : "05" line before \
                        "04" line, in line %d.') % i)
                complementary_info_type = line[45:48]
                if complementary_info_type in ('   ', 'LIB'):
                    name_append = ' ' + line[48:118].strip()
                    vals_line['name'] += name_append
                    vals_line['unique_import_id'] += name_append
            elif rec_type == '07':
                if iban != line_iban:
                    raise UserError(
                        _('Error CFONB File, account line is differente from \
                        the last account line %d.') % i)
                end_balance = self._parse_cfonb_amount(line[90:104], decimals)

                if transactions:
                    st_name = self._get_cfonb_st_name(iban,
                                                      start_date_str,
                                                      end_date_str)
                    transactions = self._cfonb_unify_transaction(transactions)
                    vals_bank_statement = {'name': st_name,
                                           'currency_code': currency_code,
                                           'account_number': iban,
                                           'date': start_date_str,
                                           'balance_start': start_balance,
                                           'balance_end_real': end_balance,
                                           'transactions': transactions, }

                    banks.append([currency_code, iban, [vals_bank_statement]])
                transactions = []
                currency_code = False
                decimals = False
                start_balance = end_balance = False
                start_date_str = end_date_str = False
                vals_line = False
        return banks

    @api.model
    def _cfonb_unify_transaction(self, transactions):
        """ If case there two operation in the same day, with same amount
            and same ref. """
        unique_import_ids = {}
        for transaction in transactions:
            unique_import_id = transaction['unique_import_id']
            if unique_import_id in unique_import_ids.keys():
                transaction['unique_import_id'] += '-%s' % unique_import_ids[unique_import_id]
                unique_import_ids[unique_import_id] += 1
            else:
                unique_import_ids[unique_import_id] = 1
        return transactions

    @api.multi
    def import_file(self):
        """ Import a file in French CFONB format"""
        self.ensure_one()

        cfonb = self._check_cfonb(base64.b64decode(self.data_file))
        if not cfonb:
            return super(AccountBankStatementImport, self).import_file()

        # Let the appropriate implementation module parse the file and return
        # the required data
        # The active_id is passed in context in case an implementation module
        # requires information about the wizard state (see QIF)
        banks = self._parse_file_cfonb(base64.b64decode(self.data_file))

        total_imported = 0
        all_statement_ids = []
        all_notifications = []

        for bank in banks:
            currency_code, account_number, stmts_vals = bank
            # Try to find the currency and journal in odoo
            currency, journal = self.with_context(
                journal_id=False)._find_additional_data(
                currency_code, account_number)
            if not journal:
                raise UserError(_('Can not find the account number %s.')
                                % account_number)
            # Prepare statement data to be used for bank statements creation
            stmts_vals = self._complete_stmts_vals(stmts_vals,
                                                   journal,
                                                   account_number,)
            # Create the bank statements
            statement_ids, notifications = self._create_bank_statements_cfonb(
                stmts_vals)
            all_statement_ids.extend(statement_ids)
            all_notifications.extend(notifications)
            total_imported += len(statement_ids)
            # Now that the import worked out, set it as the
            # bank_statements_source of the journal
            journal.bank_statements_source = 'file_import'

        # Finally dispatch to reconciliation interface
        if total_imported == 0:
            raise UserError(_('You have already imported that file.'))
        action = self.env.ref('account.action_bank_reconcile_bank_statements')
        return {'name': action.name,
                'tag': action.tag,
                'context': {'statement_ids': all_statement_ids,
                            'notifications': all_notifications,
                            },
                'type': 'ir.actions.client',
                }

    def _create_bank_statements_cfonb(self, stmts_vals):
        """ Create new bank statements from imported values,
        filtering out already imported transactions,
        and returns data used by the reconciliation widget """
        BankStatement = self.env['account.bank.statement']
        BankStatementLine = self.env['account.bank.statement.line']

        # Filter out already imported transactions and create statements
        statement_ids = []
        ignored_statement_lines_import_ids = []
        for st_vals in stmts_vals:
            filtered_st_lines = []
            for line_vals in st_vals['transactions']:
                if 'unique_import_id' not in line_vals \
                   or not line_vals['unique_import_id'] \
                   or not bool(BankStatementLine.sudo().search(
                       [('unique_import_id',
                         '=',
                         line_vals['unique_import_id'])], limit=1)):
                    if line_vals['amount'] != 0:
                        # Some banks, like ING, create a line for free charges.
                        # We just skip those lines as there's a
                        # 'non-zero' constraint
                        # on the amount of account.bank.statement.line
                        filtered_st_lines.append(line_vals)
                else:
                    ignored_statement_lines_import_ids.append(
                        line_vals['unique_import_id'])
                    if 'balance_start' in st_vals:
                        st_vals['balance_start'] += float(line_vals['amount'])

            if len(filtered_st_lines) > 0:
                # Remove values that won't be used to create records
                st_vals.pop('transactions', None)
                st_vals.pop('currency_code', None)
                st_vals.pop('account_number', None)
                for line_vals in filtered_st_lines:
                    line_vals.pop('account_number', None)
                # Create the satement
                st_vals['line_ids'] = [
                    [0, False, line] for line in filtered_st_lines]
                statement_ids.append(BankStatement.create(st_vals).id)

        # Prepare import feedback
        notifications = []
        num_ignored = len(ignored_statement_lines_import_ids)
        if num_ignored > 0:
            notifications += [{
                'type': 'warning',
                'message': _("%d transaction(s) had already been imported and \
                                were ignored.") % num_ignored,
                'details': {
                    'name': _('Already imported items'),
                    'model': 'account.bank.statement.line',
                    'ids': BankStatementLine.search([
                        ('unique_import_id', 'in',
                         ignored_statement_lines_import_ids)
                    ]).ids
                }
            }]
        return statement_ids, notifications
