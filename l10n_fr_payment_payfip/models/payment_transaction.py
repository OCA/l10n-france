from datetime import datetime, timedelta
import logging
import uuid
from werkzeug import urls

from odoo import _, api, fields, models
from odoo.tools import float_round
from odoo.exceptions import ValidationError

from ..controllers.main import PayFIPController

_logger = logging.getLogger(__name__)


class PayFIPTransaction(models.Model):
    # region Private attributes
    _inherit = 'payment.transaction'
    # endregion

    # region Default methods
    # endregion

    # region Fields declaration
    payfip_operation_identifier = fields.Char(
        string='Operation identifier',
        help='Reference of the request of TX as stored in the provider database',
    )

    payfip_return_url = fields.Char(
        string='Return URL',
    )

    payfip_sent_to_webservice = fields.Boolean(
        string="Sent to PayFIP webservice",
        default=False,
    )

    payfip_state = fields.Selection(
        string="PayFIP state",
        selection=[
            ('P', "Effective payment (P)"),
            ('V', "Effective payment (V)"),
            ('A', "Abandoned payment (A)"),
            ('R', "Other cases (R)"),
            ('Z', "Other cases (Z)"),
            ('U', "Unknown"),
        ]
    )

    payfip_amount = fields.Float(
        string="PayFIP amount",
    )

    # endregion

    def create(self, vals):
        res = super(PayFIPTransaction, self).create(vals)
        if res.provider_id.code == 'payfip':
            prec = self.env['decimal.precision'].precision_get('Product Price')
            email = res.partner_email
            amount = int(float_round(res.amount * 100.0, prec))
            reference = res.reference.replace('-', ' ')
            provider_reference = '%.15d' % int(
                uuid.uuid4().int % 899999999999999)
            res.provider_reference = provider_reference
            idop = res.provider_id.payfip_get_id_op_from_web_service(
                email, amount, reference, provider_reference)
            res.payfip_operation_identifier = idop
        return res

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'payfip':
            return res

        base_url = self.provider_id.get_base_url()
        if self.provider_id.state == 'enabled':
            saisie_value = 'W'
        elif self.provider_id.state == 'activation':
            saisie_value = 'X'
        else:
            saisie_value = 'T'

        return {
            'api_url': PayFIPController._payment_url,
            'numcli': self.provider_id.payfip_customer_number,
            'exer': fields.Datetime.now().year,
            'refdet': self.provider_reference,
            'objet': self.reference,
            'montant': self.amount,
            'mel': self.partner_email,
            'urlnotif': self.provider_id.payfip_notification_url,
            'urlredirect': self.provider_id.payfip_redirect_url,
            'saisie': saisie_value,
        }

    @api.model
    def _get_tx_from_notification_data(self, provider, data):
        """ Override of payment to find the transaction based on Payfip data.

        param str provider: The provider of the provider that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider, data)
        if provider != 'payfip':
            return tx

        reference = data
        tx = self.sudo().search(
            [('payfip_operation_identifier', '=', reference), ('provider_code', '=', 'payfip')])
        if not tx:
            raise ValidationError(
                "PayFIP: " +
                _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, feedback_data):
        data = self.provider_id.payfip_get_result_from_web_service(
            feedback_data)
        refdet = data.get('refdet', False)
        self.provider_reference = refdet
        if data.get('code'):
            self._set_pending()
        result = data.get('resultrans', False)
        self.ensure_one()
        if not result:
            self._set_pending()

        payfip_amount = int(data.get('montant', 0)) / 100
        if result in ['P', 'V']:
            self._set_done()
            self.write({
                'payfip_state': result,
                'payfip_amount': payfip_amount,
            })
            return True
        elif result in ['A']:
            message = 'Received notification for PayFIP payment %s: set as canceled' % self.reference
            _logger.info(message)
            self._set_canceled()
            self.write({
                'payfip_state': result,
                'payfip_amount': payfip_amount,
            })
            return True
        elif result in ['R', 'Z']:
            message = 'Received notification for PayFIP payment %s: set as error' % self.reference
            _logger.info(message)
            self._set_error(
                state_message=message
            )
            self.write({
                'payfip_state': result,
                'payfip_amount': payfip_amount,
            })
            return True
