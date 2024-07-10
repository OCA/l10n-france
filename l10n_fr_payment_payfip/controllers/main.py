import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class PayFIPController(http.Controller):
    _payment_url = '/payment/payfip/pay'
    _return_url = '/payment/payfip/dpn'
    _notification_url = '/payment/payfip/ipn'

    @http.route(_payment_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False, save_session=False)
    def payfip_pay(self, **post):
        reference = post.pop('objet', False)
        amount = float(post.pop('montant', 0))
        return_url = post.pop('urlredirect', '/payment/status')
        tx = request.env['payment.transaction'].sudo().search([('reference', '=', reference), ('amount', '=', amount)])
        if tx and tx.provider_id.code == 'payfip':
            # PayFIP doesn't accept two attempts with the same operation identifier, we check if transaction has
            # already sent and recreate it in this case.
            if tx.payfip_sent_to_webservice:
                tx = tx.copy({
                    'reference': request.env['payment.transaction'].get_next_reference(tx.reference),
                })

            tx.write({
                'payfip_return_url': return_url,
                'payfip_sent_to_webservice': True,
            })
            return werkzeug.utils.redirect('{url}?idop={idop}'.format(
                url="https://www.payfip.gouv.fr/tpa/paiementws.web",
                idop=tx.payfip_operation_identifier,
            ))
        else:
            return werkzeug.utils.redirect('/')

    @http.route(_notification_url, type='http', auth='public', methods=['POST'], csrf=False, save_session=False)
    def payfip_ipn(self, **post):
        """Process PayFIP IPN."""
        _logger.debug('Beginning PayFIP IPN form_feedback with post data %s', pprint.pformat(post))
        if not post or not post.get('idop'):
            raise ValidationError("No idOp found for transaction on PayFIP")

        idop = post.get('idop', False)
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data('payfip', idop)
        tx_sudo._handle_notification_data('payfip', idop)

        return ''

    @http.route(_return_url, type="http", auth="public", methods=["POST", "GET"], csrf=False, save_session=False)
    def payfip_dpn(self, **post):
        """Process PayFIP DPN."""
        _logger.debug('Beginning PayFIP DPN form_feedback with post data %s', pprint.pformat(post))

        idop = post.get('idop', False)
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data('payfip', idop)
        tx_sudo._handle_notification_data('payfip', idop)

        return request.redirect('/payment/status')
