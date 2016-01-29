# -*- encoding: utf-8 -*-
##############################################################################
#
#    account_bank_statement_import_fr_cfonb module for Odoo
#    Copyright (C) 2014-2015 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>

#    Copyright (C) 2016 Iguana-Yachts
#    @author Florent de Labarre <florent.mirieu@gmail.com> - add multi-account - use IBAN account (only france)
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
import string
from datetime import datetime
from openerp import models, fields, api, _
from openerp.exceptions import Warning

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
        
        
    def _RIBwithoutkey2IBAN(self,banque, guichet, compte):
        # http://fr.wikipedia.org/wiki/Clé_RIB#V.C3.A9rifier_un_RIB_avec_une_formule_Excel
        # calcul clé rib :
        lettres = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        chiffres = "12345678912345678923456789"
        # subst letters if needed
        for char in compte:
            if char in lettres:
                achar = char.upper()
                achiffre = chiffres[lettres.find(achar)]
                compte = compte.replace(char, achiffre)
        reste = ( 89*int(banque) + 15*int(guichet) + 3*int(compte) ) % 97
        cle = 97 - reste
        
        #conversion rib to IBAN, france seulement:
        rib = str(banque)+str(guichet)+str(compte)+str(cle)
        tmp_iban = int("".join(str(int(c,36)) for c in rib+"FR00"))
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
            raise Warning(
                _('The file is empty.'))
                
        bank_code = guichet_code = account_number = currency_code = False
        decimals = start_balance = False
        start_balance = end_balance = start_date_str = end_date_str = False
        vals_line = False
        bank = []
        data_line = []
        #Line in list, use to '05' type line 
        for line in data_file.splitlines():
            data_line.append(line)

        for i in range(0,len(data_line)):
            line = data_line[i]
            _logger.debug("Line %d: %s" % (i, line))
            if not line:
                continue
            if len(line) != 120:
                line = line[0:120]
                #raise Warning(
                #    _('Line %d is %d caracters long. All lines of a '
                #        'CFONB bank statement file must be 120 caracters '
                #        'long.')
                #    % (i, len(line)))
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
            line_iban = self._RIBwithoutkey2IBAN(line_bank_code, line_guichet_code, line_account_number)
            
            if date_cfonb_str != '      ':
                date_dt = datetime.strptime(date_cfonb_str, '%d%m%y')
                date_str = fields.Date.to_string(date_dt)


            if rec_type == '01':
                iban = line_iban
                start_balance = self._parse_cfonb_amount(
                    line[90:104], decimals)
                start_date_str = date_str

            if rec_type == '04':
                if iban != line_iban:
                    raise Warning(
                        _('Error CFONB File, account line is differente from the last account line %d.') % i)
            
                bank_account_id = partner_id = False
                amount = self._parse_cfonb_amount(line[90:104], decimals)
                ref = line[81:88].strip()  # This is not unique
                name = line[48:79].strip()
                j=1
                try:
                    while data_line[i+j][0:2] == '05':
                        name += ' %s' % data_line[i+j][48:79].strip()
                        j+=1
                except:
                    pass
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
                transactions.append(vals_line)

            if rec_type == '07':
                if iban != line_iban:
                    raise Warning(
                        _('Error CFONB File, account line is differente from the last account line %d.') % i)
            
                end_date_str = date_str
                end_balance = self._parse_cfonb_amount(line[90:104], decimals)
                vals_bank_statement = {'currency_code':currency_code,
                                       'account_number':iban,
                                       'name': str(line_account_number),
                                        'date': start_date_str,
                                        'balance_start': start_balance,
                                        'balance_end_real': end_balance,
                                        'transactions': transactions,
                    }
                bank.append(vals_bank_statement)
                #empty
                transactions = []
                bank_code = guichet_code = account_number = currency_code = False
                decimals = start_balance = False
                start_balance = end_balance = start_date_str = end_date_str = False
                vals_line = False
                
        return bank
