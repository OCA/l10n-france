# Copyright 2024 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from base64 import b64encode
from urllib.parse import parse_qs

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentAcquirerCommon


@tagged("post_install", "-at_install", "external", "-standard")
class TestPaymentMonetico(PaymentAcquirerCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.monetico = cls.env.ref("payment_monetico.payment_acquirer_monetico")
        cls.monetico.write(
            {
                "state": "test",
                "monetico_ept": "1234567",
                "monetico_company_code": "company_1",
                "monetico_secret": "12345678901234567890123456789012345678P0",
            }
        )

    @classmethod
    def _from_qs(cls, qs):
        return {k: v[0] for k, v in parse_qs(qs).items()}

    @freeze_time("2024-04-09 14:08:37")
    def test_monetico_form_render(self):
        self.assertEqual(self.monetico.state, "test", "test without test environment")

        self.env["payment.transaction"].create(
            {
                "acquirer_id": self.monetico.id,
                "amount": 100.0,
                "reference": "SO404",
                "currency_id": self.currency_euro.id,
                "partner_country_id": self.country_france.id,
            }
        )
        order_ctx = b64encode(
            json.dumps(
                dict(
                    billing=dict(
                        firstName="Norbert",
                        lastName="Buyer",
                        mobilePhone="+32-12345678",
                        addressLine1="Huge Street 2/543",
                        city="Sin City",
                        postalCode="1000",
                        country="BE",
                        email="norbert.buyer@example.com",
                        stateOrProvince=None,
                    )
                )
            ).encode("utf-8")
        ).decode("utf-8")

        self.assertEqual(
            self.monetico.render(
                "SO404", 100.0, self.currency_euro.id, values=self.buyer_values
            ).decode("utf-8"),
            """
            <input type="hidden" name="data_set" data-remove-me="" data-action-url="https://p.monetico-services.com/test/paiement.cgi"/>
            <input type="hidden" name="version" value="3.0"/>
            <input type="hidden" name="TPE" value="1234567"/>
            <input type="hidden" name="contexte_commande" value="%s"/>
            <input type="hidden" name="date" value="09/04/2024:14:08:37"/>
            <input type="hidden" name="montant" value="100.00EUR"/>
            <input type="hidden" name="reference" value="SO404"/>
            <input type="hidden" name="MAC" value="00076752218d88aec2c9f1a33cb0c1f3fccaac61"/>
            <input type="hidden" name="url_retour_ok" value="http://localhost:8069/payment/monetico/return/"/>
            <input type="hidden" name="url_retour_err" value="http://localhost:8069/payment/monetico/return/"/>
            <input type="hidden" name="lgue" value="EN"/>
            <input type="hidden" name="societe" value="company_1"/>
            <input type="hidden" name="mail" value="norbert.buyer@example.com"/>
        """  # noqa
            % order_ctx,
        )

    def test_monetico_form_management_success(self):
        self.assertEqual(self.monetico.state, "test", "test without test environment")
        # Monetico sample post data
        monetico_post_data = self._from_qs(
            "TPE=1234567"
            "&date=05%2f12%2f2006%5fa%5f11%3a55%3a23"
            "&montant=62%2e75EUR"
            "&reference=SO100x1"
            "&MAC=A384F76DBD3A59B2F7B019F3574589217CAFB2CE"
            "&texte-libre=LeTexteLibre"
            "&code-retour=paiement"
            "&cvx=oui"
            "&vld=1208"
            "&brand=VI"
            "&status3ds=1"
            "&numauto=010101"
            "&originecb=FRA"
            "&bincb=12345678"
            "&hpancb=74E94B03C22D786E0F2C2CADBFC1C00B004B7C45"
            "&ipclient=127%2e0%2e0%2e1"
            "&originetr=FRA"
            "&modepaiement=CB"
            "&veres=Y"
            "&pares=Y"
        )

        tx = self.env["payment.transaction"].create(
            {
                "amount": 62.75,
                "acquirer_id": self.monetico.id,
                "currency_id": self.currency_euro.id,
                "reference": "SO100x1",
                "partner_name": "Norbert Buyer",
                "partner_country_id": self.country_france.id,
            }
        )

        tx.form_feedback(monetico_post_data, "monetico")
        self.assertEqual(
            tx.state, "done", "Monetico: validation did not put tx into done state"
        )
        self.assertEqual(
            tx.acquirer_reference,
            "SO100x1",
            "Monetico: validation did not update tx id",
        )

    def test_monetico_form_management_error(self):
        self.assertEqual(self.monetico.state, "test", "test without test environment")
        # Monetico sample post data
        monetico_post_data = self._from_qs(
            "TPE=9000001"
            "&date=05%2f10%2f2011%5fa%5f15%3a33%3a06"
            "&montant=1%2e01EUR"
            "&reference=SO100x2"
            "&MAC=DE96CB30E9239E2D5AE03063799C9B76F3F9FA60"
            "&textelibre=Ceci+est+un+test%2c+ne+pas+tenir+compte%2e"
            "&code-retour=Annulation"
            "&cvx=oui"
            "&vld=0912"
            "&brand=MC"
            "&status3ds=-1"
            "&motifrefus=filtrage"
            "&originecb=FRA"
            "&bincb=12345678"
            "&hpancb=764AD24CFABBB818E8A7DC61D4D6B4B89EA837ED"
            "&ipclient=10%2e45%2e166%2e76"
            "&originetr=inconnue"
            "&modepaiement=CB"
            "&veres="
            "&pares="
            "&filtragecause=4-"
            "&filtragevaleur=FRA-"
        )
        tx = self.env["payment.transaction"].create(
            {
                "amount": 1.01,
                "acquirer_id": self.monetico.id,
                "currency_id": self.currency_euro.id,
                "reference": "SO100x2",
                "partner_name": "Norbert Buyer",
                "partner_country_id": self.country_france.id,
            }
        )
        tx.form_feedback(monetico_post_data, "monetico")
        self.assertEqual(
            tx.state,
            "cancel",
        )

    @freeze_time("2024-04-09 14:08:37")
    def test_monetico_form_formats(self):
        self.assertEqual(self.monetico.state, "test", "test without test environment")
        # Make an instance local copy to avoid modifying the original:
        self.buyer_values = dict(self.buyer_values)
        # Test out of bounds values to ensure they are properly formatted:
        self.buyer_values["billing_partner_name"] = (
            "Noooooooooooooooooooooooooooooooooooooooooooorbert "
            "Buuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuyer"
        )
        self.buyer_values["billing_partner_address"] = (
            "Huge Street Address that is too long, reaaaaaally too long "
            "and will be split into multiple lines that will fit within the "
            "allowed length as much as possible as determined by the acquirer."
        )
        self.buyer_values[
            "billing_partner_city"
        ] = "Siiiiiiiiiiiiiiiiiiiiiiiiiiiiin Ciiiiiiiiiityyyyyyyyyyyyy"
        self.buyer_values["billing_partner_zip"] = "12345678909876543210"
        self.buyer_values["billing_partner_email"] = (
            "noooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo"
            "oooooooooooooooooooooooooooooooooooooooooooooooooooooooooorbert."
            "buuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu"
            "uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuyer@example.com"
        )

        self.env["payment.transaction"].create(
            {
                "acquirer_id": self.monetico.id,
                "amount": 100.0,
                "reference": "SO404",
                "currency_id": self.currency_euro.id,
                "partner_country_id": self.country_france.id,
            }
        )

        order_ctx = b64encode(
            json.dumps(
                dict(
                    billing=dict(
                        firstName="Noooooooooooooooooooooooooooooooooooooooooooo",
                        lastName="Buuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu",
                        mobilePhone="+32-12345678",
                        addressLine1="Huge Street Address that is too long, reaaaaaally",
                        city="Siiiiiiiiiiiiiiiiiiiiiiiiiiiiin Ciiiiiiiiiityyyyyy",
                        postalCode="1234567890",
                        country="BE",
                        email="noooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo"
                        "oooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooorbert."
                        "buuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu"
                        "uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuyer@example.co",
                        stateOrProvince=None,
                        addressLine2="too long and will be split into multiple lines",
                        addressLine3="that will fit within the allowed length as much as",
                    )
                )
            ).encode("utf-8")
        ).decode("utf-8")

        self.assertEqual(
            self.monetico.render(
                "SO404", 100.0, self.currency_euro.id, values=self.buyer_values
            ).decode("utf-8"),
            """
            <input type="hidden" name="data_set" data-remove-me="" data-action-url="https://p.monetico-services.com/test/paiement.cgi"/>
            <input type="hidden" name="version" value="3.0"/>
            <input type="hidden" name="TPE" value="1234567"/>
            <input type="hidden" name="contexte_commande" value="%s"/>
            <input type="hidden" name="date" value="09/04/2024:14:08:37"/>
            <input type="hidden" name="montant" value="100.00EUR"/>
            <input type="hidden" name="reference" value="SO404"/>
            <input type="hidden" name="MAC" value="b6a8c77a1e55af009876d0d5d1136c2111087ebb"/>
            <input type="hidden" name="url_retour_ok" value="http://localhost:8069/payment/monetico/return/"/>
            <input type="hidden" name="url_retour_err" value="http://localhost:8069/payment/monetico/return/"/>
            <input type="hidden" name="lgue" value="EN"/>
            <input type="hidden" name="societe" value="company_1"/>
            <input type="hidden" name="mail" value="norbert.buyer@example.com"/>
        """  # noqa
            % order_ctx,
        )

    @freeze_time("2024-04-09 14:08:37")
    def test_monetico_form_bad_mail_phone(self):
        self.assertEqual(self.monetico.state, "test", "test without test environment")
        # Make an instance local copy to avoid modifying the original:
        self.buyer_values = dict(self.buyer_values)
        self.buyer_values["billing_partner_email"] = "test@"
        self.buyer_values["billing_partner_phone"] = "24"

        self.env["payment.transaction"].create(
            {
                "acquirer_id": self.monetico.id,
                "amount": 100.0,
                "reference": "SO404",
                "currency_id": self.currency_euro.id,
                "partner_country_id": self.country_france.id,
            }
        )

        order_ctx = b64encode(
            json.dumps(
                dict(
                    billing=dict(
                        firstName="Norbert",
                        lastName="Buyer",
                        mobilePhone=None,
                        addressLine1="Huge Street 2/543",
                        city="Sin City",
                        postalCode="1000",
                        country="BE",
                        email=None,
                        stateOrProvince=None,
                    )
                )
            ).encode("utf-8")
        ).decode("utf-8")

        self.assertEqual(
            self.monetico.render(
                "SO404", 100.0, self.currency_euro.id, values=self.buyer_values
            ).decode("utf-8"),
            """
            <input type="hidden" name="data_set" data-remove-me="" data-action-url="https://p.monetico-services.com/test/paiement.cgi"/>
            <input type="hidden" name="version" value="3.0"/>
            <input type="hidden" name="TPE" value="1234567"/>
            <input type="hidden" name="contexte_commande" value="%s"/>
            <input type="hidden" name="date" value="09/04/2024:14:08:37"/>
            <input type="hidden" name="montant" value="100.00EUR"/>
            <input type="hidden" name="reference" value="SO404"/>
            <input type="hidden" name="MAC" value="942d02d04903f7d8ccd886cebd3522e4698f7732"/>
            <input type="hidden" name="url_retour_ok" value="http://localhost:8069/payment/monetico/return/"/>
            <input type="hidden" name="url_retour_err" value="http://localhost:8069/payment/monetico/return/"/>
            <input type="hidden" name="lgue" value="EN"/>
            <input type="hidden" name="societe" value="company_1"/>
            <input type="hidden" name="mail" value="norbert.buyer@example.com"/>
        """  # noqa
            % order_ctx,
        )
