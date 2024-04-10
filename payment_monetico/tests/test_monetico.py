# Copyright 2024 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from base64 import b64encode
from contextlib import contextmanager
from unittest.mock import patch

from freezegun import freeze_time
from werkzeug import urls
from werkzeug.exceptions import Forbidden

from odoo.exceptions import ValidationError
from odoo.http import _request_stack
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment_monetico.controllers.main import MoneticoController
from odoo.addons.payment_monetico.tests.common import MoneticoCommon


@tagged("post_install", "-at_install")
class TestPaymentMonetico(MoneticoCommon):
    @classmethod
    @contextmanager
    def fake_request_context(cls):
        class FakeRequest:
            def redirect(self, *args, **kwargs):
                pass

        request = FakeRequest()
        request.env = cls.env
        _request_stack.push(request)

        try:
            yield request
        finally:
            _request_stack.pop()

    def _build_url(self, route):
        return urls.url_join("http://127.0.0.1:8069", route)

    @freeze_time("2024-04-09 14:08:37")
    def test_redirect_form_values(self):
        self.patch(
            type(self.env["base"]), "get_base_url", lambda _: "http://127.0.0.1:8069"
        )

        tx = self._create_transaction(flow="redirect")

        with mute_logger("odoo.addons.payment.models.payment_transaction"):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(
            processing_values["redirect_form_html"]
        )
        form_inputs = form_info["inputs"]

        self.assertEqual(form_info["action"], self.monetico.monetico_test_url)
        self.assertEqual(form_inputs["version"], self.monetico.monetico_version)
        self.assertEqual(form_inputs["TPE"], self.monetico.monetico_ept)
        self.assertEqual(
            form_inputs["contexte_commande"],
            b64encode(
                json.dumps(
                    dict(
                        billing=dict(
                            name="Norbert Buyer",
                            mobilePhone="0032 12 34 56 78",
                            addressLine1="Huge Street 2/543",
                            city="Sin City",
                            postalCode="1000",
                            country="BE",
                            email="norbert.buyer@example.com",
                            stateOrProvince=None,
                        )
                    )
                ).encode("utf-8")
            ).decode("utf-8"),
        )
        self.assertEqual(form_inputs["date"], "09/04/2024:14:08:37")
        self.assertEqual(form_inputs["montant"], "111111.00EUR")
        self.assertEqual(form_inputs["reference"], self.reference)
        self.assertEqual(form_inputs["MAC"], "7310b3050b02bb8905ac4f38f765c9f4f8d1ee36")
        return_url = self._build_url(MoneticoController._return_url)
        self.assertEqual(
            form_inputs["url_retour_ok"],
            return_url,
        )
        self.assertEqual(
            form_inputs["url_retour_err"],
            return_url,
        )
        self.assertEqual(
            form_inputs["lgue"],
            "EN",
        )
        self.assertEqual(
            form_inputs["societe"],
            self.monetico.monetico_company_code,
        )
        self.assertEqual(form_inputs["mail"], "norbert.buyer@example.com")

    def test_feedback_processing(self):
        # Unknown transaction
        with self.assertRaises(ValidationError):
            self.env["payment.transaction"]._handle_notification_data(
                "monetico", self.notification_data
            )

        # Confirmed transaction
        tx = self._create_transaction("redirect")
        self.env["payment.transaction"]._handle_notification_data(
            "monetico", self.notification_data
        )
        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.provider_reference, self.reference)

        # Cancelled transaction
        self.reference = "Test Transaction 2"
        tx = self._create_transaction("redirect")

        self.env["payment.transaction"]._handle_notification_data(
            "monetico", self.error_data
        )
        self.assertEqual(tx.state, "cancel")

    @mute_logger("odoo.addons.payment_monetico.controllers.main")
    def test_webhook_notification_confirms_transaction(self):
        """Test the processing of a webhook notification."""
        tx = self._create_transaction("redirect")
        with patch(
            "odoo.addons.payment_monetico.controllers.main.MoneticoController"
            "._verify_notification_signature"
        ), self.fake_request_context():
            controller = MoneticoController()
            controller.monetico_return_from_checkout(**self.notification_data)
        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment_monetico.controllers.main")
    def test_webhook_notification_triggers_signature_check(self):
        """Test that receiving a webhook notification triggers a signature check."""
        self._create_transaction("redirect")
        with patch(
            "odoo.addons.payment_monetico.controllers.main.MoneticoController"
            "._verify_notification_signature"
        ) as signature_check_mock, patch(
            "odoo.addons.payment.models.payment_transaction.PaymentTransaction"
            "._handle_notification_data"
        ), self.fake_request_context():
            controller = MoneticoController()
            controller.monetico_webhook(**self.notification_data)
            self.assertEqual(signature_check_mock.call_count, 1)

    def test_accept_notification_with_valid_signature(self):
        """Test the verification of a notification with a valid signature."""
        tx = self._create_transaction("redirect")
        self._assert_does_not_raise(
            Forbidden,
            MoneticoController._verify_notification_signature,
            self.notification_data,
            tx,
        )

    @mute_logger("odoo.addons.payment_monetico.controllers.main")
    def test_reject_notification_with_missing_signature(self):
        """Test the verification of a notification with a missing signature."""
        tx = self._create_transaction("redirect")
        payload = dict(self.notification_data, MAC=None)
        self.assertRaises(
            Forbidden, MoneticoController._verify_notification_signature, payload, tx
        )

    @mute_logger("odoo.addons.payment_monetico.controllers.main")
    def test_reject_notification_with_invalid_signature(self):
        """Test the verification of a notification with an invalid signature."""
        tx = self._create_transaction("redirect")
        payload = dict(self.notification_data, MAC="dummy")
        self.assertRaises(
            Forbidden, MoneticoController._verify_notification_signature, payload, tx
        )
