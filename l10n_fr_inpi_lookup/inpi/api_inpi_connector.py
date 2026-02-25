# Copyright 2024 Le Filament (https://le-filament.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from datetime import datetime
from urllib.parse import urlencode

import requests
from jwt import JWT
from requests.exceptions import HTTPError
from urllib3._collections import HTTPHeaderDict

from odoo import _, fields, models
from odoo.exceptions import UserError

from .inpi_models import InpiResponse, RolePourEntreprise

MAX_PARAM = 100
MAX_RESPONSE = 50
logger = logging.getLogger(__name__)


class ApiInpi(models.Model):
    _name = "api.inpi"
    _description = "API inpi"

    # ------------------------------------------------------
    # Fields declaration
    # ------------------------------------------------------
    company = fields.Many2one("res.company", required=True, ondelete="cascade")
    token_validity_date = fields.Datetime(
        "Token expiration date",
        help="Token expiration date",
    )
    access_token = fields.Char()
    url = fields.Char(default="https://registre-national-entreprises.inpi.fr/api")
    # ------------------------------------------------------
    # SQL Constraints
    # ------------------------------------------------------

    # ------------------------------------------------------
    # Default methods
    # ------------------------------------------------------

    # ------------------------------------------------------
    # Computed fields / Search Fields
    # ------------------------------------------------------

    # ------------------------------------------------------
    # Onchange / Constraints
    # ------------------------------------------------------

    # ------------------------------------------------------
    # CRUD methods (ORM overrides)
    # ------------------------------------------------------

    # ------------------------------------------------------
    # Actions
    # ------------------------------------------------------

    # ------------------------------------------------------
    # Business methods
    # ------------------------------------------------------

    def _compute_country(self, zipcode):
        domtom2xmlid = {
            "971": "gp",
            "972": "mq",
            "973": "gf",
            "974": "re",
            "975": "pm",  # Saint Pierre and Miquelon
            "976": "yt",  # Mayotte
            "977": "bl",  # Saint-Barthélemy
            "978": "mf",  # Saint-Martin
            "986": "wf",  # Wallis-et-Futuna
            "987": "pf",  # Polynésie française
            "988": "nc",  # Nouvelle calédonie
        }
        country_id = self.env.ref("base.fr").id
        if (
            isinstance(zipcode, str)
            and len(zipcode) == 5
            and zipcode[:3] in domtom2xmlid
        ):
            country_xmlid = f"base.{domtom2xmlid[zipcode[:3]]}"
            country_id = self.env.ref(country_xmlid).id
        return country_id

    def _call_api(self, url, call_type, **kwargs):
        logger.info(f"Calling {url}")
        try:
            if call_type == "get":
                response = requests.get(
                    url, timeout=self.company.inpi_timeout, **kwargs
                )
            elif call_type == "post":
                response = requests.post(
                    url, timeout=self.company.inpi_timeout, **kwargs
                )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection to {url} failed. Error: {e}")
            raise e
        except requests.exceptions.RequestException as e:
            logger.error("Error: %s", e)
            raise e
        except Exception as e:
            raise e

        return response.json(), response.headers

    def api_get(self, url, **kwargs):
        return self._call_api(url, "get", **kwargs)

    def api_post(self, url, **kwargs):
        return self._call_api(url, "post", **kwargs)

    def _get_data(self, url, params=None, headers=None):
        if not headers:
            headers = {}
        if not self.token_validity_date or datetime.today() > self.token_validity_date:
            self._generate_access_token()

        headers.update({"Authorization": f"Bearer {self.access_token}"})

        response, response_headers = self.api_get(
            url=self.url + url,
            verify=True,
            params=params,
            headers=headers,
        )

        try:
            page = int(response_headers.get("pagination-page", 1))
            nb_page = int(response_headers.get("pagination-max-page", 1))
        except ValueError:
            page = 1
            nb_page = 1

        if nb_page > 1:
            while page <= nb_page:
                page += 1
                headers["page"] = str(page)
                r, response_headers = self.api_get(
                    url=self.url + url,
                    verify=True,
                    params=params,
                    headers=headers,
                )
                response += r

        return response

    def _generate_access_token(self):
        if not self.company.inpi_user or not self.company.inpi_pass:
            raise UserError(
                _(f"Inpi acces not configured on company {self.company.name}")
            )

        try:
            response, headers = self.api_post(
                url=self.url + "/sso/login",
                verify=True,
                json={
                    "username": self.company.inpi_user,
                    "password": self.company.inpi_pass,
                },
            )
            if response.get("error"):
                raise UserError(_("API Error: \n%s") % (response.get("error"),))
            else:
                token = response.get("token")
                token_reader = JWT()
                token_dict = token_reader.decode(token, do_verify=False)
                self.write(
                    {
                        "access_token": token,
                        "token_validity_date": datetime.fromtimestamp(
                            token_dict.get("exp")
                        ),
                    }
                )
        except HTTPError as e:
            raise UserError(_(f"API Error: \n {e}")) from e
        except Exception as e:
            raise e from e

    @staticmethod
    def _get_siret(personne):
        if personne and personne.identite.entreprise.nicSiege:
            return (
                personne.identite.entreprise.siren
                + personne.identite.entreprise.nicSiege
            )
        elif (
            personne
            and personne.etablissementPrincipal
            and personne.etablissementPrincipal.descriptionEtablissement.siret
        ):
            return personne.etablissementPrincipal.descriptionEtablissement.siret
        return None

    @staticmethod
    def _get_name(personne, is_personne_morale):
        if is_personne_morale and personne.identite.entreprise:
            return personne.identite.entreprise.denomination
        elif (
            not is_personne_morale
            and personne.identite.entrepreneur.descriptionPersonne
        ):
            f_names = personne.identite.entrepreneur.descriptionPersonne.prenoms
            return (
                f"{personne.identite.entrepreneur.descriptionPersonne.nom} "
                f"{' '.join(f_names)}"
            )
        else:
            return "Nom inconnu"

    @staticmethod
    def _get_siege(personne):
        if personne:
            ets_prin = personne.etablissementPrincipal

            if (
                ets_prin
                and ets_prin.descriptionEtablissement.rolePourEntreprise
                == RolePourEntreprise.SIEGE_ETS_PRIN.value
            ):
                return ets_prin

            ets_secondaires = personne.autresEtablissements

            for ets in ets_secondaires:
                if (
                    ets.descriptionEtablissement.rolePourEntreprise
                    == RolePourEntreprise.SIEGE.value
                ):
                    return ets

            # si dissolution on renvoi l adresse du siege fermé
            for ets in ets_secondaires:
                if (
                    ets.descriptionEtablissement.rolePourEntreprise
                    == RolePourEntreprise.SIEGE_FERME.value
                ):
                    return ets
        return None

    @staticmethod
    def _get_inpi_address(adresse):
        voie = []
        data = {"street": "", "cedex": "", "street2": "", "zip": "", "city": ""}

        if adresse.numVoiePresent:
            voie.append(adresse.numVoie)
        if adresse.indiceRepetitionPresent:
            voie.append(adresse.indiceRepetition)
        if adresse.typeVoiePresent:
            voie.append(adresse.typeVoie)
        if adresse.voiePresent:
            voie.append(adresse.voie)
        if adresse.datePriseEffetAdressePresent:
            data["date_prise_effet"] = adresse.datePriseEffetAdresse

        if voie:
            data["street"] = " ".join(voie)
        if adresse.cedexPresent:
            data["cedex"] = adresse.cedex
        if adresse.complementLocalisationPresent:
            data["street2"] = adresse.complementLocalisation
        if adresse.codePostalPresent:
            data["zip"] = adresse.codePostal
        if adresse.communePresent:
            data["city"] = adresse.commune
        return data

    @staticmethod
    def _get_date_creation(inpi_data):
        if inpi_data.formality.typePersonne == "M":
            personne = inpi_data.formality.content.personneMorale
        else:
            personne = inpi_data.formality.content.personnePhysique

        if personne:
            if (
                inpi_data.formality.content.natureCreation
                and inpi_data.formality.content.natureCreation.dateCreation
            ):
                return inpi_data.formality.content.natureCreation.dateCreation
            elif (
                personne.identite.entreprise and personne.identite.entreprise.dateImmat
            ):
                return personne.identite.entreprise.dateImmat
            elif (
                personne.etablissementPrincipal
                and personne.etablissementPrincipal.activites
            ):
                return personne.etablissementPrincipal.activites[0].dateDebut
        return ""

    def inpi_prepare_partner_from_data(self, inpi_response, with_natural_person=True):
        if inpi_response.formality.typePersonne == "M":
            personne = inpi_response.formality.content.personneMorale
            is_personne_morale = True
        else:
            if not with_natural_person:
                return False
            personne = inpi_response.formality.content.personnePhysique
            is_personne_morale = False

        active = True
        if (
            inpi_response.formality.content.natureCessation
            and personne.detailCessationEntreprise.get("dateEffet", "")
        ):
            active = False

        if personne and is_personne_morale:
            siege = self._get_siege(personne)
            if siege and siege.adresse:
                adresse = self._get_inpi_address(siege.adresse)
            else:
                adresse = {}
        elif personne and not is_personne_morale:
            adresse = self._get_inpi_address(personne.adresseEntreprise.adresse)
        else:
            adresse = {}

        country_id = self._compute_country(adresse.get("zip"))
        if (
            personne.identite.entreprise
            and personne.identite.entreprise.effectifSalarie is not None
        ):
            staff = personne.identite.entreprise.effectifSalarie
        else:
            staff = None

        return {
            "name": self._get_name(personne, is_personne_morale),
            "street": f"{adresse.get('street', '')} {adresse.get('cedex', '')}",
            "zip": adresse.get("zip", ""),
            "city": adresse.get("city", ""),
            "country_id": country_id,
            "siren": inpi_response.siren,
            "siret": self._get_siret(personne),
            "creation_date": self._get_date_creation(inpi_response),
            "ape": personne.identite.entreprise.codeApe,
            "legal_type": personne.identite.entreprise.formeJuridique,
            "active": active,
            "staff": staff,
        }

    def get_handler(self):
        current_company = self.env.company
        inpi = self.env["api.inpi"]

        if not current_company.inpi_pass or not current_company.inpi_user:
            raise UserError(
                _(f"Inpi acces not configured on company {current_company.name}")
            )

        inpi_handler = inpi.search([("company", "=", current_company.id)])
        if not inpi_handler:
            inpi_handler = self.create({"company": current_company.id})

        return inpi_handler

    def get_data_by_name(self, name, rows=30, **kwargs):
        params = HTTPHeaderDict()
        params.add(key="pageSize", val=rows)
        params.add(key="companyName", val=name)

        for key in kwargs:
            params.add(key=key, val=kwargs.get(key))

        url = f"/companies?{urlencode(params)}"
        return [InpiResponse(**company_data) for company_data in self._get_data(url)]

    def get_data_by_siren(self, siren):
        url = f"/companies/{siren}"
        return InpiResponse(**self._get_data(url))
