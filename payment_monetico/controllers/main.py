# Copyright 2024 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import pprint

import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MoneticoController(http.Controller):
    _notify_url = "/payment/monetico/webhook/"
    _return_url = "/payment/monetico/return/"

    def monetico_validate_data(self, **post):
        monetico = request.env["payment.acquirer"].search(
            [("provider", "=", "monetico")], limit=1
        )
        values = dict(post)
        shasign = values.pop("MAC", False)
        if shasign.upper() != monetico._monetico_generate_shasign(values).upper():
            _logger.debug("Monetico: validated data")
            return (
                request.env["payment.transaction"]
                .sudo()
                .form_feedback(post, "monetico")
            )
        _logger.warning("Monetico: data are corrupted")
        return False

    @http.route(
        "/payment/monetico/webhook/",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def monetico_webhook(self, **post):
        """Monetico IPN."""
        _logger.info(
            "Beginning Monetico IPN form_feedback with post data %s",
            pprint.pformat(post),
        )
        if not post:
            _logger.warning("Monetico: received empty notification; skip.")
        else:
            self.monetico_validate_data(**post)
        return ""

    @http.route(
        "/payment/monetico/return",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def monetico_return(self, **post):
        """Monetico DPN."""
        try:
            _logger.info(
                "Beginning Monetico DPN form_feedback with post data %s",
                pprint.pformat(post),
            )
            self.monetico_validate_data(**post)
        except Exception:
            pass
        return werkzeug.utils.redirect("/payment/process")
