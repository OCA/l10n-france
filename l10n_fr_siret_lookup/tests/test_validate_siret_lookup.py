# Copyright 2025 Le Filament (https://le-filament.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from unittest.mock import patch

from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestStructure(TransactionCase):
    @classmethod
    def setUpClass(cls):
        def check_vies(vat_number, timeout=10):
            if cls.vies_timeout:
                raise Exception("Timeout")
            return {"valid": vat_number == "FR58944716448"}

        super().setUpClass()
        cls.env.user.company_id.vat_check_vies = True
        cls.vies_timeout = False
        cls.env.user.company_id.force_vat_siret_lookup = False
        cls._vies_check_func = check_vies
        cls._partner_odoo_fr_vals = {
            "name": "ODOO FR",
            "street": "3087 Rue DE LA GARE",
            "zip": "59299",
            "city": "BOESCHEPE",
            "country_id": cls.env.ref("base.fr"),
            "lang": "fr_FR",
            "siret": "94471644800013",
            "nic": "00013",
            "siren": "944716448",
            "vat": "FR58944716448",
            "vies_valid": True,
        }
        cls._partner_oca_fr_vals = {
            "name": "ODOO COMMUNITY ASSOCIATION FRANCE",
            "street": "920 ROUTE DE L'ISLE SUR SORGUE",
            "zip": "84250",
            "city": "LE THOR",
            "country_id": cls.env.ref("base.fr"),
            "lang": "fr_FR",
            "siret": "99151642800018",
            "nic": "00018",
            "siren": "991516428",
            "vat": "FR64991516428",
            "vies_valid": False,
        }
        cls.env["res.lang"]._activate_lang("fr_FR")

    def test_lookup(self):
        # Mock opendatasoft API call
        def mock_api_call(
            self, query, raise_if_fail=False, exclude_dead=False, rows=10
        ):
            if query.startswith("siren:944716448") or query.startswith(
                "siret:94471644800013"
            ):
                return {
                    "nhits": 1,
                    "parameters": {
                        "dataset": ["economicref-france-sirene-v3@public"],
                        "q": "siren:944716448 AND etablissementsiege:oui",
                        "rows": 10,
                        "start": 0,
                        "format": "json",
                        "timezone": "UTC",
                        "fields": [
                            "datefermetureunitelegale",
                            "datefermetureetablissement",
                            "denominationunitelegale",
                            "l1_adressage_unitelegale",
                            "adresseetablissement",
                            "codepostaletablissement",
                            "libellecommuneetablissement",
                            "siren",
                            "nic",
                            "codedepartementetablissement",
                            "siret",
                            "categorieentreprise",
                            "datecreationunitelegale",
                            "activiteprincipaleunitelegale",
                            "divisionunitelegale",
                            "naturejuridiqueunitelegale",
                            "trancheeffectifsunitelegale",
                            "etatadministratifetablissement",
                        ],
                    },
                    "records": [
                        {
                            "datasetid": "economicref-france-sirene-v3@public",
                            "recordid": "97596c5f8d966090f36dcdf55083cd1839cf14d5",
                            "fields": {
                                "libellecommuneetablissement": "BOESCHEPE",
                                "codepostaletablissement": "59299",
                                "adresseetablissement": "3087 Rue DE LA GARE",
                                "siret": "94471644800013",
                                "nic": "00013",
                                "siren": "944716448",
                                "naturejuridiqueunitelegale": "Soci\u00e9t\u00e9 \u00e0"
                                " responsabilit\u00e9 limit\u00e9e"
                                "(sans autre indication)",
                                "divisionunitelegale": "\u00c9dition de logiciels",
                                "etatadministratifetablissement": "Actif",
                                "codedepartementetablissement": "59",
                                "datecreationunitelegale": "2025-05-16",
                                "activiteprincipaleunitelegale": "58.29C",
                                "denominationunitelegale": "ODOO FR",
                            },
                            "record_timestamp": "2025-07-07T07:38:00Z",
                        }
                    ],
                }
            elif query.startswith("siren:991516428") or query.startswith(
                "siret:99151642800018"
            ):
                return {
                    "nhits": 1,
                    "parameters": {
                        "dataset": ["economicref-france-sirene-v3@public"],
                        "q": "siren:991516428 AND etablissementsiege:oui",
                        "rows": 10,
                        "start": 0,
                        "format": "json",
                        "timezone": "UTC",
                        "fields": [
                            "datefermetureunitelegale",
                            "datefermetureetablissement",
                            "denominationunitelegale",
                            "l1_adressage_unitelegale",
                            "adresseetablissement",
                            "codepostaletablissement",
                            "libellecommuneetablissement",
                            "siren",
                            "nic",
                            "codedepartementetablissement",
                            "siret",
                            "categorieentreprise",
                            "datecreationunitelegale",
                            "activiteprincipaleunitelegale",
                            "divisionunitelegale",
                            "naturejuridiqueunitelegale",
                            "trancheeffectifsunitelegale",
                            "etatadministratifetablissement",
                        ],
                    },
                    "records": [
                        {
                            "datasetid": "economicref-france-sirene-v3@public",
                            "recordid": "97596c5f8d966090f36dcdf55083cd1839cf14d6",
                            "fields": {
                                "libellecommuneetablissement": "LE THOR",
                                "codepostaletablissement": "84250",
                                "adresseetablissement": "920 ROUTE DE L'ISLE SUR "
                                "SORGUE",
                                "siret": "99151642800018",
                                "nic": "00018",
                                "siren": "991516428",
                                "naturejuridiqueunitelegale": "Association déclarée",
                                "divisionunitelegale": "Services d'information",
                                "etatadministratifetablissement": "Actif",
                                "codedepartementetablissement": "84",
                                "datecreationunitelegale": "2025-08-14",
                                "activiteprincipaleunitelegale": "63.99C",
                                "denominationunitelegale": "ODOO COMMUNITY ASSOCIATION "
                                "FRANCE",
                            },
                            "record_timestamp": "2025-07-07T07:38:00Z",
                        }
                    ],
                }
            else:
                return {}

        # Using mocked functions for API call to opendatasoft and VIES
        with (
            patch(
                "odoo.addons.l10n_fr_siret_lookup.models.res_partner.check_vies",
                type(self)._vies_check_func,
            ),
            patch.object(
                type(self.env["res.partner"]),
                "_opendatasoft_get_raw_data",
                mock_api_call,
            ),
        ):
            # For each of the 2 partners (one with valid VAT, one with invalid VAT)
            for vals in [self._partner_odoo_fr_vals, self._partner_oca_fr_vals]:
                # We test the various on change :
                # - Setting SIREN, SIRET or VAT in "name" field
                # - Setting SIREN in "siren" field
                # - Setting SIRET in "siret" field
                # - Setting VAT in "vat" field
                for form_input, field in [
                    ("name", "siren"),
                    ("name", "siret"),
                    ("name", "vat"),
                    ("siren", "siren"),
                    ("siret", "siret"),
                    ("vat", "vat"),
                ]:
                    with (
                        Form(self.env["res.partner"]) as partner_form,
                        (
                            self.assertLogs(level=logging.WARNING)
                            if self.vies_timeout
                            else self.assertNoLogs(level=logging.WARNING)
                        ) as logs,
                    ):
                        # First we set company type so that name becomes readwrite
                        partner_form.company_type = "company"
                        # Set the field value in form_input
                        partner_form[form_input] = vals[field]

                        # Catch warning on VIES timeout only
                        if self.vies_timeout:
                            self.assertEqual(len(logs.records), 1)
                            self.assertEqual(logs.records[0].levelno, logging.WARNING)

                        # Check all values wrt dict stored in test
                        for value in vals:
                            # Compare strings
                            if isinstance(vals[value], str):
                                # Specific test for "vat" field
                                # In any of the following cases "vat" should be false :
                                # - if we check VIES, VAT is invalid AND no timeout
                                # - if we check VIES, timeout and VAT is not forced
                                # - if we do not check VIES and VAT is not forced
                                if value == "vat" and (
                                    (
                                        self.env.user.company_id.vat_check_vies
                                        and not vals["vies_valid"]
                                        and not self.vies_timeout
                                    )
                                    or (
                                        self.env.user.company_id.vat_check_vies
                                        and self.vies_timeout
                                        and not self.env.user.company_id.force_vat_siret_lookup  # noqa: E501
                                    )
                                    or (
                                        not self.env.user.company_id.vat_check_vies
                                        and not self.env.user.company_id.force_vat_siret_lookup  # noqa: E501
                                    )
                                ):
                                    self.assertFalse(
                                        partner_form[value],
                                        f"{value} was invalid and therefore not "
                                        "filled in name",
                                    )
                                    continue
                                # Otherwise it should be the "vat" value from dict
                                self.assertEqual(
                                    partner_form[value],
                                    vals[value],
                                    f"{value} was detected from {field} "
                                    "filled in name",
                                )
                            # Specific test for vies_valid
                            elif value == "vies_valid":
                                # It should be true only if we check VIES
                                # and get a valid response
                                if (
                                    self.env.user.company_id.vat_check_vies
                                    and vals["vies_valid"]
                                    and not self.vies_timeout
                                ):
                                    self.assertTrue(
                                        partner_form[value], "VIES verification is OK"
                                    )
                                # In any other case we expect it to be False
                                else:
                                    self.assertFalse(
                                        partner_form.vies_valid, "vies_valid is False"
                                    )


class TestStructureNoVIES(TestStructure):
    allow_inherited_tests_method = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.company_id.vat_check_vies = False


class TestStructureVIESForce(TestStructure):
    allow_inherited_tests_method = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.company_id.force_vat_siret_lookup = True


class TestStructureVIESTimeoutNoForce(TestStructure):
    allow_inherited_tests_method = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vies_timeout = True


class TestStructureVIESTimeoutForce(TestStructure):
    allow_inherited_tests_method = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vies_timeout = True
        cls.env.user.company_id.force_vat_siret_lookup = True


class TestStructureNoVIESForce(TestStructure):
    allow_inherited_tests_method = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.company_id.vat_check_vies = False
        cls.env.user.company_id.force_vat_siret_lookup = True
