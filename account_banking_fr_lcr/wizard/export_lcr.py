# -*- coding: utf-8 -*-
##############################################################################
#
#    French Letter of Change module for Odoo
#    Copyright (C) 2014-2015 Akretion (http://www.akretion.com)
#    @author: Alexis de Lattre <alexis.delattre@akretion.com>
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

from openerp import models, fields, api, workflow, _
from openerp.exceptions import Warning
import base64
import logging
logger = logging.getLogger(__name__)

try:
    from unidecode import unidecode
except ImportError:
    logger.debug('Cannot import unidecode')

LCR_DATE_FORMAT = '%d%m%y'


class BankingExportLcrWizard(models.TransientModel):
    _name = 'banking.export.lcr.wizard'
    _description = 'Export French LCR File'
    _rec_name = 'filename'

    state = fields.Selection([
        ('create', 'Create'),
        ('finish', 'Finish'),
        ], string='State', readonly=True, default='create')
    total_amount = fields.Float(
        string='Total Amount', readonly=True)
    file = fields.Binary(
        string='LCR CFONB File', readonly=True)
    filename = fields.Char(string='Filename', readonly=True)
    payment_order_ids = fields.Many2many(
        'payment.order', 'wiz_lcr_payorders_rel', 'wizard_id',
        'payment_order_id', string='Payment Orders', readonly=True)

    @api.model
    def create(self, vals=None):
        if vals is None:
            vals = {}
        payment_order_ids = self.env.context.get('active_ids', [])
        vals.update({
            'payment_order_ids': [[6, 0, payment_order_ids]],
        })
        return super(BankingExportLcrWizard, self).create(vals)

    @api.model
    def _prepare_field(self, field_name, field_value, size):
        '''This function is designed to be inherited.'''
        if not field_value:
            raise Warning(
                _("The field '%s' is empty or 0. It should have a non-null "
                    "value.")
                % field_name)
        try:
            value = unidecode(field_value)
            unallowed_ascii_chars = [
                '"', '#', '$', '%', '&', ';', '<', '>', '=', '@',
                '[', ']', '^', '_', '`', '{', '}', '|', '~', '\\', '!',
                ]
            for unallowed_ascii_char in unallowed_ascii_chars:
                value = value.replace(unallowed_ascii_char, '-')
        except:
            raise Warning(
                _("Cannot convert the field '%s' to ASCII")
                % field_name)
        value = value.upper()
        # Cut if too long
        value = value[0:size]
        # enlarge if too small
        if len(value) < size:
            value = value.ljust(size, ' ')
        assert len(value) == size, 'The length of the field is wrong'
        return value

    @api.model
    def _get_rib_from_iban(self, partner_bank):
        # I do NOT want to add a dependancy on l10n_fr_rib, because
        # we plan to remove the module in the near future
        # So I consider that IBAN MUST be given in the res.partner.bank
        # of type 'rib'
        if partner_bank.state == 'rib' and not partner_bank.acc_number:
            raise Warning(
                _("For the bank account '%s' of partner '%s', the bank "
                    "account type is 'RIB and optional IBAN' and the IBAN "
                    "field is empty, but, starting from 2014, we consider "
                    "that the IBAN is required. Please write the IBAN on "
                    "this bank account.")
                % (partner_bank.name_get()[0][1],
                    partner_bank.partner_id.name))
        elif partner_bank.state != 'iban':
            raise Warning(
                _("For the bank account '%s' of partner '%s', the Bank "
                    "Account Type should be 'IBAN'.")
                % (partner_bank.name_get()[0][1],
                    partner_bank.partner_id.name))
        iban = partner_bank.acc_number.replace(' ', '')
        if iban[0:2] != 'FR':
            raise Warning(
                _("LCR are only for French bank accounts. The IBAN '%s' "
                    "of partner '%s' is not a French IBAN.")
                % (partner_bank.acc_number, partner_bank.partner_id.name))
        assert len(iban) == 27, 'French IBANs must have 27 caracters'
        return {
            'code_banque': iban[4:9],
            'code_guichet': iban[9:14],
            'numero_compte': iban[14:25],
            'cle_rib': iban[25:27],
            }

    @api.model
    def _prepare_first_cfonb_line(self, lcr_export):
        '''Generate the header line of the CFONB file'''
        code_enregistrement = '03'
        code_operation = '60'
        numero_enregistrement = '00000001'
        numero_emetteur = '000000'  # It is not needed for LCR
        # this number is only required for old national direct debits
        today_str = fields.Date.context_today(self)
        today_dt = fields.Date.from_string(today_str)
        date_remise = today_dt.strftime(LCR_DATE_FORMAT)
        raison_sociale_cedant = self._prepare_field(
            u'Raison sociale du cédant',
            lcr_export.payment_order_ids[0].company_id.name, 24)
        domiciliation_bancaire_cedant = self._prepare_field(
            u'Domiciliation bancaire du cédant',
            lcr_export.payment_order_ids[0].mode.bank_id.bank_name, 24)
        code_entree = '3'
        code_dailly = ' '
        code_monnaie = 'E'
        rib = self._get_rib_from_iban(
            lcr_export.payment_order_ids[0].mode.bank_id)
        ref_remise = self._prepare_field(
            u'Référence de la remise',
            lcr_export.payment_order_ids[0].reference, 11)
        cfonb_line = ''.join([
            code_enregistrement,
            code_operation,
            numero_enregistrement,
            numero_emetteur,
            ' ' * 6,
            date_remise,
            raison_sociale_cedant,
            domiciliation_bancaire_cedant,
            code_entree,
            code_dailly,
            code_monnaie,
            rib['code_banque'],
            rib['code_guichet'],
            rib['numero_compte'],
            ' ' * (16 + 6 + 10 + 15),
            # Date de valeur is left empty because it is only for
            # "remise à l'escompte" and we do
            # "Encaissement, crédit forfaitaire après l’échéance"
            ref_remise,
            ])
        assert len(cfonb_line) == 160, 'LCR CFONB line must have 160 chars'
        cfonb_line += '\r\n'
        return cfonb_line

    @api.model
    def _prepare_cfonb_line(
            self, line, requested_date, transactions_count):
        '''Generate each debit line of the CFONB file'''
        # I use French variable names because the specs are in French
        code_enregistrement = '06'
        code_operation = '60'
        numero_enregistrement = str(transactions_count + 1).zfill(8)
        reference_tire = self._prepare_field(
            u'Référence tiré', line.communication, 10)
        rib = self._get_rib_from_iban(line.bank_id)

        nom_tire = self._prepare_field(
            u'Nom tiré', line.partner_id.name, 24)
        nom_banque = self._prepare_field(
            u'Nom banque', line.bank_id.bank_name, 24)
        code_acceptation = '0'
        montant_centimes = str(line.amount_currency * 100).split('.')[0]
        zero_montant_centimes = montant_centimes.zfill(12)
        today_str = fields.Date.context_today(self)
        today_dt = fields.Date.from_string(today_str)
        date_creation = today_dt.strftime(LCR_DATE_FORMAT)
        requested_date_dt = fields.Date.from_string(requested_date)
        date_echeance = requested_date_dt.strftime(LCR_DATE_FORMAT)
        reference_tireur = reference_tire

        cfonb_line = ''.join([
            code_enregistrement,
            code_operation,
            numero_enregistrement,
            ' ' * (6 + 2),
            reference_tire,
            nom_tire,
            nom_banque,
            code_acceptation,
            ' ' * 2,
            rib['code_banque'],
            rib['code_guichet'],
            rib['numero_compte'],
            zero_montant_centimes,
            ' ' * 4,
            date_echeance,
            date_creation,
            ' ' * (4 + 1 + 3 + 3 + 9),
            reference_tireur,
            ])
        assert len(cfonb_line) == 160, 'LCR CFONB line must have 160 chars'
        cfonb_line += '\r\n'
        return cfonb_line

    def _prepare_final_cfonb_line(self, total_amount, transactions_count):
        '''Generate the last line of the CFONB file'''
        code_enregistrement = '08'
        code_operation = '60'
        numero_enregistrement = str(transactions_count + 2).zfill(8)
        montant_total_centimes = str(total_amount * 100).split('.')[0]
        zero_montant_total_centimes = montant_total_centimes.zfill(12)
        cfonb_line = ''.join([
            code_enregistrement,
            code_operation,
            numero_enregistrement,
            ' ' * (6 + 12 + 24 + 24 + 1 + 2 + 5 + 5 + 11),
            zero_montant_total_centimes,
            ' ' * (4 + 6 + 10 + 15 + 5 + 6),
            ])
        assert len(cfonb_line) == 160, 'LCR CFONB line must have 160 chars'
        return cfonb_line

    @api.multi
    def create_lcr(self):
        '''Creates the LCR CFONB file.'''
        self.ensure_one()
        lcr_export = self[0]

        cfonb_string = self._prepare_first_cfonb_line(lcr_export)
        total_amount = 0.0
        order_ref = []
        transactions_count = 0
        for order in lcr_export.payment_order_ids:
            if order.reference:
                order_ref.append(order.reference.replace('/', '-'))
            # Iterate each payment lines
            for line in order.bank_line_ids:
                if line.currency.name != 'EUR':
                    raise Warning(
                        _("The currency of payment line '%s' is '%s'. "
                            "To be included in a French LCR, the currency "
                            "must be EUR.")
                        % (line.name, line.currency.name))
                transactions_count += 1
                cfonb_string += self._prepare_cfonb_line(
                    line, line.date, transactions_count)
                total_amount += line.amount_currency

        cfonb_string += self._prepare_final_cfonb_line(
            total_amount, transactions_count)

        filename = '%s%s.txt' % ('LCR_', '-'.join(order_ref))
        lcr_export.write({
            'file': base64.encodestring(cfonb_string),
            'total_amount': total_amount,
            'filename': filename,
            'state': 'finish',
            })

        action = {
            'name': 'LCR File',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': lcr_export.id,
            'target': 'new',
            }
        return action

    @api.multi
    def save_lcr(self):
        '''Mark the LCR file as 'sent' and the payment order as 'done'.'''
        self.ensure_one()
        lcr_export = self[0]
        for order in lcr_export.payment_order_ids:
            workflow.trg_validate(
                self._uid, 'payment.order', order.id, 'done', self._cr)
            self.env['ir.attachment'].create({
                'res_model': 'payment.order',
                'res_id': order.id,
                'name': lcr_export.filename,
                'datas': lcr_export.file,
                })
        return True
