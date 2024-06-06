
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger
from odoo.tests import tagged, users
from odoo import _, fields
from odoo.tests import HttpCase
import pytest

from .common import PayFIPCommon
from ..controllers.main import PayFIPController


@pytest.mark.skip(
    reason=(
        "No way of currently testing this with pytest-odoo because:\n"
        "* that require an open odoo port\n"
        "* the open port should use the same pgsql transaction\n"
        "* payment.transaction class must be mocked\n\n"
        "Please use odoo --test-enable to launch those test"
    )
)
@tagged('post_install', '-at_install')
class PayFIPHttpTest(PayFIPCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        @classmethod
        def base_url(cls):
            return cls.env["ir.config_parameter"].get_param("web.base.url")
        cls.base_url = base_url
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.PaymentTransaction = self.env["payment.transaction"]
        self.calls = 0

        def handle_feedback_data(_, provider, data):
            self.assertEqual(provider, "payfip")
            self.assertEqual(
                data, {"idop": "5e64f6f2-7b4b-4ebe-aa6c-7493f5e443af"})
            self.calls += 1
            return self.PaymentTransaction.new({"reference": "5e64f6f2-7b4b-4ebe-aa"})

        self.PaymentTransaction._patch_method(
            "_handle_feedback_data", handle_feedback_data)
        self.addCleanup(self.PaymentTransaction._revert_method,
                        "_handle_feedback_data")

    def test_return_get(self):
        idop = "5e64f6f2-7b4b-4ebe-aa6c-7493f5e443af"
        url = self._build_url(PayFIPController._return_url)
        response = self.opener.get(
            url + "?idop=" + idop)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.calls, 1)
        response = self.opener.post(
            url, data={"idop": idop})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.calls, 2)

    def test_notify_post(self):
        idop = "5e64f6f2-7b4b-4ebe-aa6c-7493f5e443af"
        url = self._build_url(PayFIPController._notification_url)
        response = self.opener.post(
            url, data={"idop": idop})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.calls, 1)


@tagged('post_install', '-at_install')
class PayFIPTest(PayFIPCommon):

    def test_processing_values(self):
        tx = self.create_transaction(flow='redirect')  # Only flow implemented
        return_url = self._build_url(PayFIPController._return_url)
        notification_url = self._build_url(PayFIPController._notification_url)

        expected_values = {
            'numcli': self.provider.payfip_customer_number,
            'exer': str(fields.Datetime.now().year),
            'mel': 'norbert.buyer@example.com',
            'montant': "1111.11",
            'objet': self.reference,
            'refdet': tx.provider_reference,
            'saisie': 'T',
            'urlnotif': notification_url,
            'urlredirect': return_url
        }

        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()
        redirect_form_data = self._extract_values_from_html_form(
            processing_values['redirect_form_html'])

        self.assertEqual(
            redirect_form_data['action'], self.provider.payfip_get_form_action_url())

        self.assertDictEqual(
            expected_values,
            redirect_form_data['inputs'],
            "PayFIP: invalid inputs specified in the redirect form.",
        )

    def test_feedback_processing(self):
        # typical data posted by payFIP after client has successfully paid
        payfip_post_data = {
            'dattrans': u'06012023',
            'exer': u'2023',
            'heurtrans': u'1100',
            'idOp': u'93be8501-9184-4e63-81b3-53b5a7f4d69a',
            'mel': u'norbert.buyer@example.com',
            'montant': u'111111',
            'numauto': u'A55A',
            'numcli': self.provider.payfip_customer_number,
            'objet': self.reference,
            'refdet': u'088655675121650',
            'saisie': u'T'
        }

        with self.assertRaises(ValidationError):
            self.env['payment.transaction']._handle_feedback_data(
                'payfip', payfip_post_data['idOp'])

        tx = self.create_transaction(flow='redirect')

        self.env['payment.transaction']._handle_feedback_data(
            'payfip', payfip_post_data)
        self.assertEqual(
            tx.state, 'pending', 'payfip: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.provider_reference, '088655675121650',
                         'payfip: wrong reference after receiving a valid pending notification')

        tx.write({'state': 'draft', 'provider_reference': False})

        payfip_post_data = 'd4a40f3e-5186-4e3f-a74c-213279cb82f1'
        self.env['payment.transaction']._handle_feedback_data(
            'payfip', payfip_post_data)
        self.assertEqual(
            tx.state, 'done', 'payfip: wrong state after receiving a valid done notification')
        self.assertEqual(tx.provider_reference, '088655675121650',
                         'payfip: wrong reference after receiving a valid done notification')

        tx.write({'state': 'draft', 'provider_reference': False})

        payfip_post_data = '580f47c5-dc72-40d3-86c0-ae104ef48797'
        self.env['payment.transaction']._handle_feedback_data(
            'payfip', payfip_post_data)
        self.assertEqual(
            tx.state, 'cancel', 'wrong state after receiving a valid cancel notification')
        self.assertEqual(tx.provider_reference, '088655675121650',
                         'payfip: wrong reference after receiving a valid cancel notification')

    def test_payfip_webservice(self):
        payfip_webservice_enable = self.provider._check_payfip_customer_number()
        self.assertEqual(payfip_webservice_enable, True)
