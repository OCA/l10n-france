# Copyright 2018-2022 Le Filament (<http://www.le-filament.com>)
# Copyright 2021-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

import requests

from odoo import api, models
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)
try:
    from stdnum.eu.vat import check_vies
    from stdnum.fr.siren import is_valid as siren_is_valid
    from stdnum.fr.siren import to_tva as siren_to_vat
    from stdnum.fr.siret import is_valid as siret_is_valid
except ImportError:
    logger.debug("Cannot import stdnum")

TIMEOUT = 5


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _opendatasoft_fields_list(self):
        return [
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
            # for the wizard
            "siret",
            "categorieentreprise",
            "datecreationunitelegale",
            "activiteprincipaleunitelegale",
            "divisionunitelegale",
            "naturejuridiqueunitelegale",
            "trancheeffectifsunitelegale",
            "etatadministratifetablissement",
        ]

    @api.model
    def _opendatasoft_get_raw_data(
        self, query, raise_if_fail=False, exclude_dead=False, rows=10
    ):
        assert isinstance(query, str)
        assert isinstance(rows, int) and rows > 0
        url = "https://data.opendatasoft.com/api/records/1.0/search/"
        params = {
            "dataset": "economicref-france-sirene-v3@public",
            "q": query,
            "rows": rows,
            "fields": ",".join(self._opendatasoft_fields_list()),
        }
        # It seems that datefermetureetablissement and datefermetureunitelegale
        # often have a value for a SIRET that is still open
        # For example, SIRET 55208131766522 (siège social d'EDF)
        # has datefermetureetablissement=2009-02-22
        # and datefermetureunitelegale=2018-12-01 !!!
        # So I now set exclude_dead=False by default
        if exclude_dead:
            params["q"] += (
                " AND #null(datefermetureetablissement)"
                " AND #null(datefermetureunitelegale)"
            )
        try:
            logger.info("Sending query to https://data.opendatasoft.com/api")
            logger.debug(f"url={url} params={params}")
            res = requests.get(url, params=params, timeout=TIMEOUT)
            if res.status_code in (200, 201):
                res_json = res.json()
                # from pprint import pprint
                # pprint(res_json)
                return res_json
            else:
                logger.warning(
                    f"HTTP error {res.status_code} returned by "
                    "GET on data.opendatasoft.com/api"
                )
                if raise_if_fail:
                    raise UserError(
                        self.env._(
                            "The webservice data.opendatasoft.com "
                            f"returned an HTTP error code {res.status_code}."
                        )
                    )
        except Exception as e:
            logger.warning(f"Failure in the GET request on data.opendatasoft.com: {e}")
            if raise_if_fail:
                raise UserError(
                    self.env._(
                        "Failure in the request on data.opendatasoft.com "
                        "to create or update partner from SIREN or SIRET. "
                        f"Technical error: {e}."
                    )
                ) from e
        return False

    @api.model
    def _opendatasoft_parse_record(self, raw_record, exclude_dead=False):
        res = False
        if raw_record and isinstance(raw_record, dict):
            if exclude_dead and raw_record.get("datefermetureunitelegale"):
                return res
            if exclude_dead and raw_record.get("datefermetureetablissement"):
                return res
            res = {
                "name": raw_record.get("denominationunitelegale")
                or raw_record.get("l1_adressage_unitelegale"),
                "street": raw_record.get("adresseetablissement"),
                "city": raw_record.get("libellecommuneetablissement"),
                "siren": raw_record.get("siren") and str(raw_record["siren"]) or False,
                "nic": raw_record.get("nic"),
            }
            # In feb 2022, they changed codepostaletablissement and
            # codedepartementetablissement from string to integer
            # So I now want to support both, it case they change it back !
            if raw_record.get("codepostaletablissement"):
                res["zip"] = raw_record["codepostaletablissement"]
                if isinstance(res["zip"], int):
                    res["zip"] = str(res["zip"])
                res["zip"] = res["zip"].zfill(5)

            # I don't use "codedepartementetablissement" to compute
            # the country, because it is not always set, in particular
            # for partners in Corsica
            if res.get("zip"):
                res["country_id"] = self._opendatasoft_compute_country(res["zip"])
            # set lang to French if installed
            fr_lang = self.env["res.lang"].search([("code", "=", "fr_FR")])
            if fr_lang:
                res["lang"] = "fr_FR"
            if res.get("siren"):
                vat, vies_valid = self._siren2vat_vies(res["siren"])
                res["vat"] = vat
                res["vies_valid"] = vies_valid
        return res

    @api.model
    def _opendatasoft_compute_country(self, zipcode):
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

    @api.model
    def _siren2vat_vies(self, siren, raise_if_fail=False):
        """
        Function checking VAT number generated from SIREN
        Returns 2 values :
          - char: VAT number (or None if not valid / not tested and not forced)
          - bool: vies_valid (if validated by VIES server)
        """
        vat = f"FR{siren_to_vat(siren)}"
        # Default return empty values
        empty_res = False, False
        # If we do not want to check VIES server
        if not self.env.company.vat_check_vies:
            # If we still want to use computed value without verification
            if self.env.company.force_vat_siret_lookup:
                return vat, False
            else:
                return empty_res

        logger.info(f"VIES check of VAT {vat}")
        vies_res = False
        try:
            vies_res = check_vies(vat, timeout=TIMEOUT)
            logger.debug(f"VIES answer vies_res.valid={vies_res['valid']}")
        except Exception as e:
            logger.warning(f"VIES query failed: {e}")
            if not self.env.company.vat_check_vies and raise_if_fail:
                raise UserError(
                    self.env._(f"Failed to query VIES.\nTechnical error: {e}.")
                ) from e
            # If exception is raised but we still want to force computed value
            # We return vat number and vies_valid = False
            elif self.env.company.force_vat_siret_lookup:
                return vat, False
            return empty_res
        # If VIES validates vat we return the VAT value and vies_valid = True
        # Otherwise we return False / False
        if vies_res and vies_res["valid"]:
            return vat, True
        return empty_res

    @api.model
    def _opendatasoft_get_first_result(self, query, raise_if_fail=False):
        res_json = self._opendatasoft_get_raw_data(query, raise_if_fail=raise_if_fail)
        if res_json and "records" in res_json:
            if len(res_json["records"]) > 0:
                raw_record = res_json["records"][0].get("fields")
                if raw_record:
                    return self._opendatasoft_parse_record(raw_record)
            else:
                logger.warning("The query on opendatasoft.com returned 0 records")
        return False

    @api.model
    def _opendatasoft_get_from_siren(self, siren):
        if siren and siren_is_valid(siren):
            vals = self._opendatasoft_get_first_result(
                f"siren:{siren} AND etablissementsiege:oui",
            )
            if vals and vals.get("siren") == siren:
                return vals
        return False

    @api.model
    def _opendatasoft_get_from_siret(self, siret):
        if siret and siret_is_valid(siret):
            vals = self._opendatasoft_get_first_result(f"siret:{siret}")
            if vals and vals.get("siren") and vals.get("nic"):
                vals_siret = vals["siren"] + vals["nic"]
                if vals_siret == siret:
                    return vals
        return False

    @api.onchange("siren")
    def siren_onchange(self):
        if (
            self.siren
            and siren_is_valid(self.siren)
            and not self.name
            and self.is_company
            and not self.parent_id
        ):
            if self.nic:
                # We only execute the query if the full SIRET is OK
                vals = False
                if siret_is_valid(self.siren + self.nic):
                    siret = self.siren + self.nic
                    vals = self._opendatasoft_get_from_siret(siret)
            else:
                vals = self._opendatasoft_get_from_siren(self.siren)
            if vals:
                self.update(vals)

    @api.onchange("siret")
    def siret_onchange(self):
        if (
            self.siret
            and siret_is_valid(self.siret)
            and not self.name
            and self.is_company
            and not self.parent_id
        ):
            vals = self._opendatasoft_get_from_siret(self.siret)
            if vals:
                self.update(vals)

    @api.onchange("vat")
    def vat_onchange(self):
        if (
            self.vat
            and not self.name
            and not self.siren
            and not self.siret
            and self.is_company
            and not self.parent_id
        ):
            vat = self.vat.replace(" ", "").upper()
            if vat and vat.startswith("FR") and len(vat) == 13:
                siren = vat[4:]
                if siren_is_valid(siren):
                    vals = self._opendatasoft_get_from_siren(siren)
                    if vals:
                        self.update(vals)

    @api.onchange("name")
    def siren_siret_vat_in_name_onchange(self):
        if (
            self.name
            and self.is_company
            and not self.parent_id
            and not self.siren
            and not self.nic
            and not self.siret
            and not self.street
            and not self.city
            and not self.zip
        ):
            name = self.name.replace(" ", "")
            if name:
                vals = False
                if len(name) == 9 and name.isdigit() and siren_is_valid(name):
                    vals = self._opendatasoft_get_from_siren(name)
                elif len(name) == 14 and name.isdigit() and siret_is_valid(name):
                    vals = self._opendatasoft_get_from_siret(name)
                elif (
                    len(name) == 13
                    and name[:2] == "FR"
                    and name[2:].isdigit()
                    and siren_is_valid(name[4:])
                ):
                    vals = self._opendatasoft_get_from_siren(name[4:])
                if vals:
                    self.update(vals)
