# -*- coding: utf-8 -*-
##############################################################################
#
#    account_bank_statement_import_fr_multi_cfonb module for Odoo
#    Copyright (C) 2014-2015 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#    @author Florent de Labarre
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
import base64
from openerp.addons.base.res.res_bank import sanitize_account_number

_logger = logging.getLogger(__name__)


class BankBalise(models.Model):
    _name = 'res.partner.bankbalise'
    _description = 'Bank Balise'
    _order = 'partner_id desc'
    balise_id = fields.Char('Balise', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', select=True,
                                 required=True, ondelete='cascade')
    _sql_constraints = [('balise_id',
                         'unique (balise_id)',
                         'Balise need to be unique')]


class ResPartner(models.Model):
    _inherit = 'res.partner'
    balise_ids = fields.One2many('res.partner.bankbalise', 'partner_id',
                                 string='Balises', copy=True)


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
        # http://fr.wikipedia.org/wiki/Clé_RIB#V.C3.A9rifier_un_RIB_avec_un
        # e_formule_Excel
        # calcul key rib :
        lettres = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        chiffres = "12345678912345678923456789"
        # subst letters if needed
        for char in compte:
            if char in lettres:
                achar = char.upper()
                achiffre = chiffres[lettres.find(achar)]
                compte = compte.replace(char, achiffre)
        reste = (89*int(banque) + 15*int(guichet) + 3*int(compte)) % 97
        cle = 97 - reste
        # conversion rib to IBAN, france only:
        rib = str(banque)+str(guichet)+str(compte)+str(cle)
        tmp_iban = int("".join(str(int(c, 36)) for c in rib+"FR00"))
        key = 98 - (tmp_iban % 97)
        return "FR%.2d%s" % (key, rib)

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
        bank_code = guichet_code = account_number = currency_code = False
        decimals = start_balance = False
        start_balance = end_balance = start_date_str = end_date_str = False
        vals_line = False
        bank = []
        data_line = []
        # import balise
        partner_model = self.env['res.partner']
        partners = partner_model.search_read([], ['balise_ids'])
        balise_model = self.env['res.partner.bankbalise']

        for line in data_file.splitlines():
            data_line.append(line)
        for i in range(0, len(data_line)):
            line = data_line[i]
            _logger.debug("Line %d: %s" % (i, line))
            if not line:
                continue
            if len(line) != 120:
                line = line[0:120]
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
            assert decimals == 2, 'We use 2 decimals in France!'
            date_cfonb_str = line[34:40]
            date_dt = False
            date_str = False

            line_iban = self._RIBwithoutkey2IBAN(line_bank_code,
                                                 line_guichet_code,
                                                 line_account_number)
            if date_cfonb_str != '      ':
                date_dt = datetime.strptime(date_cfonb_str, '%d%m%y')
                date_str = fields.Date.to_string(date_dt)

            if rec_type == '01':
                iban = line_iban
                start_balance = self._parse_cfonb_amount(
                    line[90:104], decimals)
                start_date_str = date_str
                anti_double = []
                ind_anti_double = 0
                currency_code = line_currency_code

            if rec_type == '04':
                if iban != line_iban:
                    raise UserError(
                        _('Error CFONB File, account line is \
                        differente from the last account line %d.') % i)
                bank_account_id = partner_id = False
                amount = self._parse_cfonb_amount(line[90:104], decimals)
                ref = line[81:88].strip()  # This is not unique
                name = line[48:79].strip()
                j = 1
                try:
                    while data_line[i+j][0:2] == '05':
                        name += ' %s' % data_line[i+j][48:79].strip()
                        j += 1
                except:
                    pass

                id_line_unique = '%s-%s-%.2f-%s' % (date_str,
                                                    ref,
                                                    amount,
                                                    name)

                # if case id_line_unique is not unique on same count 
                # (it is possible : double credit card paiement on same day), 
                # add a number to make a difference
                if id_line_unique in anti_double:
                    ind_anti_double += 1
                    id_line_unique += str(" " + str(ind_anti_double))
                    name += str(" " + str(ind_anti_double))

                anti_double.append(id_line_unique)

                # find a partner in field bank with a balise "-U-5667-U-", 
                # 5667 is the id of partner, 
                # add this balise when you do a bank transfert in bank website
                
                for partner in partners:
                    find = False 
                    # print ("#################", partner['id'])
                    if partner['balise_ids']:
                        for balise_part in partner['balise_ids']:
                            # print (balise_part)
                            balise_name = \
                                balise_model.search([('id',
                                                      '=',
                                                      balise_part)]).balise_id
                            # print ("cool", balise_name)
                            if str(balise_name) in name:
                                partner_id = partner['id']
                                # print 
                                # ("Find", name, balise_name, partner['id'])
                                find = True 
                                break
                            else:
                                partner_id = False
                    if find: 
                        break

                # context = none #{'ir_sequence_date', date_str}
                vals_line = {
                    'date': date_str,
                    'name': name,
                    'ref': ref,
                    'unique_import_id':id_line_unique,
                    'amount': amount,
                    'partner_id': partner_id,
                    'bank_account_id': bank_account_id,
                }
                transactions.append(vals_line)

            if rec_type == '07':
                if iban != line_iban:
                    raise UserError(
                        _('Error CFONB File, account line is differente from \
                        the last account line %d.') % i)

                end_date_str = date_str
                end_balance = self._parse_cfonb_amount(line[90:104], decimals)
                vals_bank_statement = {'currency_code':currency_code,
                                       'account_number':iban,
                                       # utilise la numérotation odoo
                                       'name': False, 
                                       'date': start_date_str,
                                       'balance_start': start_balance,
                                       'balance_end_real': end_balance,
                                       'transactions': transactions,
                    }
                # print( "CCCCC", currency_code, iban)
                bank.append([currency_code, iban, [vals_bank_statement]])
                transactions = []
                bank_code = guichet_code = \
                    account_number = currency_code = False
                decimals = start_balance = False
                start_balance = end_balance = \
                    start_date_str = end_date_str = False
                vals_line = False
        #print (bank)
        return bank

    @api.multi
    def import_file(self):
        """ Process the file chosen in the wizard, create bank statement(s) 
        and go to reconciliation. use for multi bank"""
        self.ensure_one()
        # Let the appropriate implementation module parse the file and return
        # the required data
        # The active_id is passed in context in case an implementation module 
        # requires information about the wizard state (see QIF)
        super_data = self.with_context(active_id=self.ids[0]).\
                        _parse_file(base64.b64decode(self.data_file))
        # print ("super", super_data)
        total_imported = 0
        all_statement_ids = []
        all_notifications = []
        for s_data in super_data:
            
            currency_code, account_number, stmts_vals = s_data
            # Check raw data
            # self._check_parsed_data(stmts_vals)
            # Try to find the currency and journal in odoo
            currency, journal = self._find_additional_data(currency_code, 
                                                           account_number)
            # If no journal found, ask the user about creating one
            if not journal:
                raise UserError(
                _('Can not find the account number %s.') % account_number)
                # The active_id is passed in context so the wizard can call 
                # import_file again once the journal is created
                # return self.with_context(active_id=self.ids[0]).
                # _journal_creation_wizard(currency, account_number)
            # Prepare statement data to be used for bank statements creation
            stmts_vals = self._complete_stmts_vals(stmts_vals, 
                                                   journal, 
                                                   account_number,)
            # Create the bank statements
            statement_ids, notifications = \
                self._create_bank_statements(stmts_vals)
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
        return {
                'name': action.name,
                'tag': action.tag,
                'context': {
                            'statement_ids': all_statement_ids,
                            'notifications': all_notifications,
                },
                'type': 'ir.actions.client',
        }

    @api.model    
    def _find_additional_data(self, currency_code, account_number):
        """ Look for a res.currency and account.journal using values 
            extracted from the
            statement and make sure it's consistent.
        """
        company_currency = self.env.user.company_id.currency_id
        journal_obj = self.env['account.journal']
        currency = None
        sanitized_account_number = sanitize_account_number(account_number)
        if currency_code:
            currency = self.env['res.currency'].search([('name',
                                                         '=ilike', 
                                                         currency_code),]
                                                         , limit=1)
            if not currency:
                raise UserError(_("No currency \
                                    found matching '%s'.") % currency_code)
            if currency == company_currency:
                currency = False

        if account_number:
            journal = journal_obj.search([('bank_acc_number',
                                           '=',
                                           account_number)], limit=1)
        return currency, journal
    @api.model    
    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        for st_vals in stmts_vals:
            st_vals['journal_id'] = journal.id

            for line_vals in st_vals['transactions']:
                unique_import_id = line_vals.get('unique_import_id')
                if unique_import_id:
                    sanitized_account_number = \
                        sanitize_account_number(account_number)
                    line_vals['unique_import_id'] = \
                        (sanitized_account_number and \
                        sanitized_account_number + '-' or '')\
                        + unique_import_id
                    # suppression de  + str(journal.id) + '-' +  
                    # afin de garder la compatibilité avec la V8
        # print ("================", stmts_vals)
        return stmts_vals

    @api.model   
    def _create_bank_statements(self, stmts_vals):
        """ Create new bank statements from imported values, 
        filtering out already imported transactions, and 
        returns data used by the reconciliation widget """
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
                                line_vals['unique_import_id'])],
                                limit=1)):
                    filtered_st_lines.append(line_vals)
                else:
                    ignored_statement_lines_import_ids.\
                        append(line_vals['unique_import_id'])
            if len(filtered_st_lines) > 0:
                # Remove values that won't be used to create records
                st_vals.pop('transactions', None)
                for line_vals in filtered_st_lines:
                    line_vals.pop('account_number', None)
                # Create the satement
                st_vals['line_ids'] = [[0, False, line] \
                                        for line in filtered_st_lines]
                statement_ids.append(BankStatement.create(st_vals).id)
        # if len(statement_ids) == 0:
        #    raise UserError(_('You have already imported that file.'))

        # Prepare import feedback
        notifications = []
        num_ignored = len(ignored_statement_lines_import_ids)
        if num_ignored > 0:
            notifications += [{
                'type': 'warning',
                'message': _("%d transactions had already been imported \
                            and were ignored.") \
                            % num_ignored if num_ignored > 1 \
                            else _("1 transaction had already been \
                            imported and was ignored."),
                'details': {
                    'name': _('Already imported items'),
                    'model': 'account.bank.statement.line',
                    'ids': BankStatementLine.search([('unique_import_id', 
                            'in', ignored_statement_lines_import_ids)]).ids
                }
            }]
        return statement_ids, notifications
