# Copyright 2021 Moka Tourisme
# @author: Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from werkzeug import urls
from lxml import objectify
from odoo import fields
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger


class TestPaymentPayfip(PaymentAcquirerCommon):

    def setUp(self):
        super().setUp()
        self.country_france = self.env.ref("base.fr")
        self.buyer_values.update({
            "partner_country": self.country_france,
            "partner_country_id": self.country_france.id,
            "partner_country_name": self.country_france.name,
            "billing_partner_country": self.country_france,
            "billing_partner_country_id": self.country_france.id,
            "billing_partner_country_name": self.country_france.name,
        })
        self.buyer.country_id = self.country_france
        self.payfip = self.env.ref("payment_payfip.payment_acquirer_payfip")

    def test_10_form_render(self):
        base_url = self.env["ir.config_parameter"].get_param("web.base.url")
        self.assertEqual(self.payfip.environment, "test", "test environment")
        # Create a draft tx
        self.env["payment.transaction"].create({
            "amount": 99.51,
            "acquirer_id": self.payfip.id,
            "currency_id": self.currency_euro.id,
            "reference": "test_ref0",
            "partner_id": self.buyer.id,
        })
        # Render form
        res = self.payfip.render(
            "test_ref0", 99.51, self.currency_euro.id, values=self.buyer_values
        )
        tree = objectify.fromstring(res)
        # Check data set
        data_set = tree.xpath("//input[@name='data_set']")
        self.assertEqual(len(data_set), 1)
        self.assertEqual(
            data_set[0].get("data-action-url"),
            "https://www.tipi.budget.gouv.fr/tpa/paiement.web",
            "Wrong post URL"
        )
        # Check fields
        expected_fields = {
            "numcli": "99999",
            "objet": "testref0",
            "montant": "9951",
            "mel": "norbert.buyer@example.com",
            "saisie": "T",
            "urlcl": urls.url_join(base_url, "/payment/payfip/return"),
        }
        for form_input in tree.input:
            name = form_input.get("name")
            value = form_input.get("value", False)
            if name == "refdet":
                self.assertNotEqual(value, False, "refdet should be set")
            elif name in expected_fields:
                self.assertEqual(
                    value, expected_fields[name], "Wrong value for %s" % name
                )

    @mute_logger(
        "odoo.addons.payment_payfip.models.payment_transaction",
        "ValidationError",
    )
    def test_20_form_feedback(self):
        self.assertEqual(self.payfip.environment, "test", "test environment")
        # Typical data posted by payfip after a successful payment
        post_data = {
            "numcli": "99999",
            "exer": "2021",
            "refdet": "xxxxxxxxxx0001",
            "objet": "test_ref20",
            "montant": "10522",
            "mel": "norbert.buyer@example.com",
            "saisie": "T",
            "resultrans": "P",
            "numauto": "00000001",
            "dattrans": "04052021",
            "heurtrans": "1325",
        }
        # Should raise unknown tx error
        with self.assertRaises(ValidationError):
            self.env["payment.transaction"].form_feedback(post_data, "payfip")
        # create tx
        tx = self.env["payment.transaction"].create({
            "amount": 105.22,
            "acquirer_id": self.payfip.id,
            "currency_id": self.currency_euro.id,
            "reference": "xxxxxxxxxx0001",
        })
        # Should raise missing refdet error
        with self.assertRaises(ValidationError):
            missing_refdet = dict(post_data, refdet=None)
            self.env["payment.transaction"].form_feedback(missing_refdet, "payfip")
        # validate it
        tx.form_feedback(post_data, "payfip")
        # check state
        self.assertEqual(
            tx.state, "done",
            "Validation did not put tx into done state",
        )
        self.assertEqual(
            tx.acquirer_reference, post_data.get("numauto"),
            "Should update acquirer reference",
        )
        self.assertEqual(
            tx.date, fields.Datetime.from_string("2021-05-04 13:25:00"),
            "Transaction date should've been updated",
        )
