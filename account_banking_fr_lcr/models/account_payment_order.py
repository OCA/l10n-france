# -*- coding: utf-8 -*-
# © 2014-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    from unidecode import unidecode
except ImportError:
    unidecode = False

LCR_DATE_FORMAT = '%d%m%y'


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    @api.model
    def _prepare_lcr_field(self, field_name, field_value, size):
        '''This function is designed to be inherited.'''
        if not field_value:
            raise UserError(_(
                "The field '%s' is empty or 0. It should have a non-null "
                "value.") % field_name)
        try:
            value = unidecode(field_value)
            unallowed_ascii_chars = [
                '"', '#', '$', '%', '&', ';', '<', '>', '=', '@',
                '[', ']', '^', '_', '`', '{', '}', '|', '~', '\\', '!',
                ]
            for unallowed_ascii_char in unallowed_ascii_chars:
                value = value.replace(unallowed_ascii_char, '-')
        except Exception:
            # seems that unidecode doesn't raise exception so might
            # be useless
            raise UserError(_(
                "Cannot convert the field '%s' to ASCII") % field_name)
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
        if partner_bank.acc_type != 'iban':
            raise UserError(_(
                "For the bank account '%s' of partner '%s', the Bank "
                "Account Type should be 'IBAN'.")
                % (partner_bank.acc_number, partner_bank.partner_id.name))
        iban = partner_bank.sanitized_acc_number
        if iban[0:2] != 'FR':
            raise UserError(_(
                "LCR are only for French bank accounts. The IBAN '%s' "
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
    def _prepare_first_cfonb_line(self):
        '''Generate the header line of the CFONB file'''
        code_enregistrement = '03'
        code_operation = '60'
        numero_enregistrement = '00000001'
        numero_emetteur = '000000'  # It is not needed for LCR
        # this number is only required for old national direct debits
        today_str = fields.Date.context_today(self)
        today_dt = fields.Date.from_string(today_str)
        date_remise = today_dt.strftime(LCR_DATE_FORMAT)
        raison_sociale_cedant = self._prepare_lcr_field(
            u'Raison sociale du cédant', self.company_id.name, 24)
        domiciliation_bancaire_cedant = self._prepare_lcr_field(
            u'Domiciliation bancaire du cédant',
            self.company_partner_bank_id.bank_id.name, 24)
        code_entree = '3'
        code_dailly = ' '
        code_monnaie = 'E'
        rib = self._get_rib_from_iban(self.company_partner_bank_id)
        ref_remise = self._prepare_lcr_field(
            u'Référence de la remise', self.name, 11)
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
    def _prepare_cfonb_line(self, line, transactions_count):
        '''Generate each debit line of the CFONB file'''
        # I use French variable names because the specs are in French
        code_enregistrement = '06'
        code_operation = '60'
        numero_enregistrement = str(transactions_count + 1).zfill(8)
        reference_tire = self._prepare_lcr_field(
            u'Référence tiré', line.communication, 10)
        rib = self._get_rib_from_iban(line.partner_bank_id)

        nom_tire = self._prepare_lcr_field(
            u'Nom tiré', line.partner_id.name, 24)
        if line.partner_bank_id.bank_id:
            nom_banque = self._prepare_lcr_field(
                u'Nom banque', line.partner_bank_id.bank_id.name, 24)
        else:
            nom_banque = ' ' * 24
        code_acceptation = '0'
        montant_centimes = str(line.amount_currency * 100).split('.')[0]
        zero_montant_centimes = montant_centimes.zfill(12)
        today_str = fields.Date.context_today(self)
        today_dt = fields.Date.from_string(today_str)
        date_creation = today_dt.strftime(LCR_DATE_FORMAT)
        requested_date_dt = fields.Date.from_string(line.date)
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
    def generate_payment_file(self):
        '''Creates the LCR CFONB file.'''
        self.ensure_one()
        if (
                self.payment_method_id.code !=
                'fr_lcr'):
            return super(AccountPaymentOrder, self).generate_payment_file()

        cfonb_string = self._prepare_first_cfonb_line()
        total_amount = 0.0
        transactions_count = 0
        eur_currency = self.env.ref('base.EUR')
        # Iterate each bank payment lines
        for line in self.bank_line_ids:
            if line.currency_id != eur_currency:
                raise UserError(_(
                    "The currency of payment line '%s' is '%s'. To be "
                    "included in a French LCR, the currency must be EUR.")
                    % (line.name, line.currency_id.name))
            transactions_count += 1
            cfonb_string += self._prepare_cfonb_line(line, transactions_count)
            total_amount += line.amount_currency

        cfonb_string += self._prepare_final_cfonb_line(
            total_amount, transactions_count)

        filename = 'LCR_%s.txt' % self.name.replace('/', '-')
        return (cfonb_string, filename)
