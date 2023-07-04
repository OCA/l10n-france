# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import socket
import logging
from pprint import pprint
logger = logging.getLogger(__name__)

try:
    import pycountry
except ImportError:
    logger.debug('Cannot import pycountry')

CAISSE_AP_TIMEOUT = 180


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        res = super()._get_payment_terminal_selection()
        res.append(("caisse_ap_ip", _("Caisse AP over IP")))
        return res

    caisse_ap_ip_mode = fields.Selection(
        [("card", "Card"), ("check", "Check")], string="Payment Mode", default="card"
    )
    caisse_ap_ip_address = fields.Char(string='Caisse-AP Payment Terminal IP Address', help="IP address or DNS name of the payment terminal that support Caisse-AP protocol over IP")
    caisse_ap_ip_port = fields.Integer(string='Caisse-AP Payment Terminal Port', help="TCP port of the payment terminal that support Caisse-AP protocol over IP", default=8888)

    @api.constrains('caisse_ap_ip_port')
    def _check_caisse_ap_ip_port(self):
        for config in self:
            if config.caisse_ap_ip_port < 1 or config.caisse_ap_ip_port > 65535:
                raise ValidationError(_("Port %s for the payment terminal is not a valid TCP port.") % config.caisse_ap_ip_port)

    @api.constrains('use_payment_terminal', 'caisse_ap_ip_address', 'caisse_ap_ip_port')
    def _check_caisse_ap_ip(self):
        for method in self:
            if method.use_payment_terminal == 'caisse_ap_ip':
                if not method.caisse_ap_ip_address:
                    raise ValidationError(_(
                        "Caisse-AP Payment Terminal IP Address is not set on Payment Method '%s'.") % method.display_name)
                if not method.caisse_ap_ip_port:
                    raise ValidationError(_(
                        "Caisse-AP Payment Terminal Port is not set on Payment Method '%s'.") % method.display_name)

    def _caisse_ap_ip_prepare_msg(self, msg_dict):
        assert isinstance(msg_dict, dict)
        for tag, value in msg_dict.items():
            assert isinstance(tag, str)
            assert len(tag) == 2
            assert isinstance(value, str)
            assert len(value) >= 1
            assert len(value) <= 999
        msg_list = []
        # Always start with tag CZ
        # the order of the other tags is unrelevant
        if 'CZ' in msg_dict:
            version = msg_dict.pop('CZ')
        else:
            version = '0300'  # 0301 ??
        assert len(version) == 4
        msg_list.append(('CZ', version))
        msg_list += list(msg_dict.items())
        msg_str = ''.join(['%s%s%s' % (tag, str(len(value)).zfill(3), value) for (tag, value) in msg_list])
        return msg_str

    @api.model
    def caisse_ap_ip_send_payment(self, data):
        # called by JS code
        print('caisse_ap_ip_send_payment data=', data)
        logger.debug('caisse_ap_ip_send_payment data=%s', data)
        amount = data.get('amount')
        payment_method_id = data['payment_method_id']
        currency_id = data['currency_id']
        currency = self.env['res.currency'].browse(currency_id)
        print('payment_method_id=', payment_method_id)
        payment_method = self.browse(payment_method_id)
# p48 - identification caisse terminal
# CZ version protocole
# CJ identifiant protocole concert : aucun intérêt, mais obligatoire
# CA numéro de caisse
# CD Type action 0 débit (achat) 1 crédit (remboursement)
# BF paiement partiel 0 refusé 1 accepté
        cur_speed_map = {  # small speed-up, and works even if pycountry not installed
            'EUR': '978',
            'XPF': '953',
            'USD': '840',  # Only because it is the default currency
        }
        if currency.name in cur_speed_map:
            cur_num = cur_speed_map[currency.name]
        else:
            try:
                cur = pycountry.currencies.get(alpha_3=currency.name)
                cur_num = cur.numeric  # it returns a string
            except Exception as e:
                logger.error("pycountry doesn't support currency '%s'. Error: %s" % (currency.name, e))
                return False
        msg_dict = {
            'CJ': '012345678901',
            'CA': '01',
            'CE': cur_num,
            'BF': '0',
            }
        amount_compare = currency.compare_amounts(amount, 0)
        if not amount_compare:
            logger.error('Amount for payment terminal is 0')
            return False  # TODO raise Error?
        elif amount_compare < 0:
            msg_dict['CD'] = '1'  # credit i.e. reimbursement
            amount_positive = amount * -1
        else:
            msg_dict['CD'] = '0'  # debit i.e. regular payment
            amount_positive = amount

# Réponse sur MESSAGE_ID : CZ0040301CJ012330538600404CA00201CD001IAE00210
# p36 Transaction
# CB = montant en centimes, longueur variable 2 à 12
# CD = action (0 pour débit ; 1 pour remboursement ; 2 pour annulation)
# CE = devise 978 pour euro
# CH : optionnel : Numéro de référence donné lors de la transaction (En fonction du type d’action demandée par la caisse, ce numéro peut être vérifié par le terminal)
        if currency.decimal_places:
            amount_cent = amount_positive * (10 ** currency.decimal_places)
        else:
            amount_cent = amount_positive
        amount_str = str(int(round(amount_cent)))
        msg_dict['CB'] = amount_str
        if len(amount_str) < 2:
            amount_str = amount_str.zfill(2)
        elif len(amount_str) > 12:
            logger.error("Amount with cents '%s' is over the maximum." % amount_str)
            return False
        if payment_method.caisse_ap_ip_mode == 'check':
            msg_dict['CC'] = '00C'
        # TODO Try/except quand l'IP n'est pas joignable
        answer = False
        with socket.create_connection((payment_method.caisse_ap_ip_address, payment_method.caisse_ap_ip_port), timeout=CAISSE_AP_TIMEOUT) as sock:
            sock.settimeout(None)
            msg_str = self._caisse_ap_ip_prepare_msg(msg_dict)
            logger.debug('data sent to payment terminal: %s' % msg_str)
            sock.send(msg_str.encode('ascii'))
            BUFFER_SIZE = 1024
            answer = sock.recv(BUFFER_SIZE)
            logger.debug("answer received from payment terminal: %s", answer.decode('ascii'))
        if answer:
            answer_dict = self._caisse_ap_ip_parse_answer(answer)
            self._caisse_ap_ip_check_answer(answer_dict, msg_dict)
            if answer_dict.get('AE') == '10':
                to_pos_dict = self._caisse_ap_ip_success_to_pos_dict(answer_dict)
                logger.debug('JSON sent back to POS: %s', to_pos_dict)
                return to_pos_dict
            elif answer_dict.get('AE') == '01':
                error_msg = self._caisse_ap_ip_failure_error_msg(answer_dict)
                raise UserError(error_msg)
        return True

    def _caisse_ap_ip_check_answer(self, answer_dict, msg_dict):
        tag_dict = {
            'CA': {'fixed_size': True, 'required': True, 'label': 'caisse'},
            'CB': {'fixed_size': False, 'required': True, 'label': 'amount'},
            'CD': {'fixed_size': True, 'required': True, 'label': 'action pay/reimb'},
            'CE': {'fixed_size': True, 'required': True, 'label': 'currency'},
            'BF': {'fixed_size': True, 'required': False, 'label': 'partial payment'},
            }
        for tag, props in tag_dict.items():
            if props['required'] and not answer_dict.get(tag):
                raise UserError(_("Caisse AP IP protocol: tag %s is required but it is not present in the answer. This should never happen!") % answer_dict.get(tag))
            if props['fixed_size'] and answer_dict.get(tag) and answer_dict[tag] != msg_dict[tag]:
                raise UserError(_("Caisse AP IP protocol: Tag %(label)s (%(tag)s) has value %(request_val)s in the request and %(answer_val)s in the answer, but these values should be identical. This should never happen!", label=props['label'], tag=tag, request_val=msg_dict[tag], answer_val=answer_dict[tag]))
            elif not props['fixed_size'] and answer_dict.get(tag):
                strip_answer = answer_dict[tag].lstrip('0')
                if msg_dict[tag] != strip_answer:
                    raise UserError(_("Caisse AP IP protocol: Tag %(label)s (%(tag)s) has value %(request_val)s in the request and %(answer_val)s in the answer, but these values should be identical. This should never happen!", label=props['label'], tag=tag, request_val=msg_dict[tag], answer_val=strip_answer))

    def _caisse_ap_ip_success_to_pos_dict(self, answer_dict):
        card_type_list = []
        cc_labels = {
            '1': 'CB contact',
            'B': 'CB sans contact',
            'C': 'Chèque',
            '2': 'Amex contact',
            'D': 'Amex sans contact',
            '3': 'CB Enseigne',
            '5': 'Cofinoga',
            '6': 'Diners',
            '7': 'CB-Pass',
            '8': 'Franfinance',
            '9': 'JCB',
            'A': 'Banque Accord',
            'I': 'CPEI',
            'E': 'CMCIC-Pay TPE',
            'U': 'CUP',
            '0': 'Autres',
            }
        ci_labels = {
            '0': 'indifférent',
            '1': 'contact',
            '2': 'sans contact',
            '3': 'piste',
            '4': 'saisie manuelle',
            }
        ticket = False
        if answer_dict.get('CC') and len(answer_dict['CC']) == 3:
            cc_tag = answer_dict['CC'].lstrip('0')
            cc_label = cc_labels.get(cc_tag, _('unknown'))
            card_type_list.append(_('Application %(label)s (code %(code)s)', label=cc_label, code=cc_tag))
            ticket = _('Card type: %s') % cc_label
        if answer_dict.get('CI') and len(answer_dict['CI']) == 1:
            card_type_list.append(_('Read mode: %(label)s (code %(code)s)', label=ci_labels.get(answer_dict['CI'], _('unknown')), code=answer_dict['CI']))

        transaction_tags = ['AA', 'AB', 'AC', 'AI', 'CD']
        transaction_id = '|'.join(['%s-%s' % (tag, answer_dict[tag]) for tag in transaction_tags if answer_dict.get(tag)])

        to_pos_dict = {
            'transaction_id': transaction_id,
            'card_type': ' - '.join(card_type_list),
            'ticket': ticket,
            }
        return to_pos_dict

    def _caisse_ap_ip_failure_error_msg(self, answer_dict):
        error_msg = _("The payment transaction has failed.")
        af_labels = {
            '00': 'Inconnu',
            '01': 'Transaction autorisé',
            '02': 'Appel phonie',
            '03': 'Forçage',
            '04': 'Refusée',
            '05': 'Interdite',
            '06': 'Abandon',
            '07': 'Non aboutie',
            '08': 'Opération non effectuée Time-out saisie',
            '09': 'Opération non effectuée erreur format message',
            '10': 'Opération non effectuée erreur sélection',
            '11': 'Opération non effectuée Abandon Opérateur',
            '12': 'Opération non effectuée type d’action demandé inconnu',
            '13': 'Devise non supportée',
            }
        if answer_dict.get('AF') and answer_dict['AF'] in af_labels:
            label = af_labels[answer_dict['AF']]
            error_msg = _("The payment transaction has failed: %s") % label
        return error_msg

    def _caisse_ap_ip_parse_answer(self, data_bytes):
        data_str = data_bytes.decode('ascii')
        logger.info('Received raw data: %s', data_str)
        data_dict = {}
        i = 0
        while i < len(data_str):
            tag = data_str[i:i + 2]
            i += 2
            size_str = data_str[i:i + 3]
            size = int(size_str)
            i += 3
            value = data_str[i:i + size]
            data_dict[tag] = value
            i += size
        logger.info('Answer dict:')
        pprint(data_dict)
        return data_dict
