# Copyright 2021 Moka Tourisme
# @author: Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PayfipController(http.Controller):

    @http.route(['/payment/payfip/return'], type='http', auth='none', csrf=False)
    def payfip_return(self, **post):
        _logger.debug(
            "PayFIP: entering form_feedback with post data %s",
            pprint.pformat(post),
        )
        try:
            request.env["payment.transaction"].sudo().form_feedback(post, "payfip")
        except Exception as e:
            _logger.exception(e)
            raise e
        return werkzeug.utils.redirect("/payment/process")
