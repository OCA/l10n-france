# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosCaisseApIpController(http.Controller):

    @http.route('/pos/caisse_ap_ip_payment_terminal_request', type='json', auth='user')
    def caisse_ap_ip_payment_terminal_request(self, **kwargs):
        print('caisse_ap_ip_payment_terminal_request self=', self)
