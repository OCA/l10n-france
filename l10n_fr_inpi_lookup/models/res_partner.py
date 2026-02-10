# Copyright 2018-2022 Le Filament (<http://www.le-filament.com>)
# Copyright 2021-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

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
    def _inpi_get_from_siren(self, siren):
        if siren and siren_is_valid(siren):
            inpi_handler = self.env["api.inpi"].get_handler()
            vals = inpi_handler.get_data_by_siren(siren)
            if not vals:
                logger.warning("The query on INPI returned 0 records")
                return False
            return inpi_handler.inpi_prepare_partner_from_data(vals)
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
            vals = self._inpi_get_from_siren(self.siren)
            if vals:
                self.update(
                    {
                        "name": vals.get("name", ""),
                        "street": vals.get("street", ""),
                        "zip": vals.get("zip", ""),
                        "city": vals.get("city", ""),
                        "country_id": vals.get("country_id", ""),
                        "siret": vals.get("siret", ""),
                    }
                )

    @api.onchange("siret")
    def siret_onchange(self):
        if (
            self.siret
            and siret_is_valid(self.siret)
            and not self.name
            and self.is_company
            and not self.parent_id
        ):
            vals = self._inpi_get_from_siren(self.siret[:9])
            if vals:
                self.update(
                    {
                        "name": vals.get("name", ""),
                        "street": vals.get("street", ""),
                        "zip": vals.get("zip", ""),
                        "city": vals.get("city", ""),
                        "country_id": vals.get("country_id", ""),
                        "siret": vals.get("siret", ""),
                    }
                )

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
                    vals = self._inpi_get_from_siren(self.siren)
                    if vals:
                        self.update(
                            {
                                "name": vals.get("name", ""),
                                "street": vals.get("street", ""),
                                "zip": vals.get("zip", ""),
                                "city": vals.get("city", ""),
                                "country_id": vals.get("country_id", ""),
                                "siret": vals.get("siret", ""),
                            }
                        )

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
                    vals = self._inpi_get_from_siren(name)
                elif len(name) == 14 and name.isdigit() and siret_is_valid(name):
                    vals = self._inpi_get_from_siren(name[:9])
                elif (
                    len(name) == 13
                    and name[:2] == "FR"
                    and name[2:].isdigit()
                    and siren_is_valid(name[4:])
                ):
                    vals = self._inpi_get_from_siren(name[4:])
                if vals:
                    self.update(
                        {
                            "name": vals.get("name", ""),
                            "street": vals.get("street", ""),
                            "zip": vals.get("zip", ""),
                            "city": vals.get("city", ""),
                            "country_id": vals.get("country_id", ""),
                            "siret": vals.get("siret", ""),
                        }
                    )
