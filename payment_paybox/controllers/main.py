# Copyright 2024 Akretion (http://www.akretion.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import pprint

import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PayBoxController(http.Controller):
    _notify_url = "/payment/paybox/webhook/"
    _return_url = "/payment/paybox/return/"

    def paybox_validate_data(self, **post):
        paybox = request.env["payment.acquirer"].search(
            [("provider", "=", "paybox")], limit=1
        )
        values = post.split("&")
        values_dict = {}
        for element in values:
            (key, value) = element.split("=")
            values_dict[key] = value
        paybox_key = values_dict.pop("key", False)
        if paybox._paybox_key_security_identification(values, paybox_key):
            _logger.debug("Paybox: validated data")
            return (
                request.env["payment.transaction"].sudo().form_feedback(post, "Paybox")
            )
        _logger.warning("Paybox: data are corrupted")
        return False

    @http.route(
        "/payment/paybox/webhook/",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def paybox_webhook(self, **post):
        """Paybox IPN."""
        _logger.info(
            "Beginning Paybox IPN form_feedback with post data %s",
            pprint.pformat(post),
        )
        if not post:
            _logger.warning("Paybox: received empty notification; skip.")
        else:
            self.paybox_validate_data(**post)
        return ""

    @http.route(
        "/payment/paybox/return",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def paybox_return(self, **post):
        """Paybox return."""
        try:
            _logger.info(
                "Beginning Paybox return form_feedback with post data %s",
                pprint.pformat(post),
            )
            self.paybox_validate_data(**post)
        except Exception:
            pass
        return werkzeug.utils.redirect("/payment/process")
