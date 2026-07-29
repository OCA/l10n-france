# Copyright 2018-2022 Le Filament (<http://www.le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, models
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)
try:
    from stdnum.eu.vat import check_vies
    from stdnum.fr.siren import to_tva as siren_to_vat
except ImportError:
    logger.debug("Cannot import stdnum")

TIMEOUT = 5


class ResPartner(models.Model):
    _inherit = "res.partner"

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

    def get_mappings_data(self, api_data):
        """
        Adding VAT and VIES_VALID to updated datas
        """
        datas = super().get_mappings_data(api_data)

        vat, vies_valid = self._siren2vat_vies(
            api_data.get("siren"), raise_if_fail=True
        )

        if vat:
            datas["vat"] = vat
            datas["vies_valid"] = vies_valid

        return datas
