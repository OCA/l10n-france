# Copyright 2018-2022 Le Filament (<http://www.le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, models
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)
try:
    from stdnum.fr.siren import is_valid as siren_is_valid
    from stdnum.fr.siret import is_valid as siret_is_valid
except ImportError:
    logger.debug("Cannot import stdnum")


class ResPartner(models.Model):
    _inherit = "res.partner"

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
                self.self.update_from_api(vals)

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
                self.self.update_from_api(vals)

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
                    self.update_from_api(vals)

    def get_mappings_data(self, api_data):
        current_company = self.env.company
        mappings = self.env["api.inpi.mapping"].search(
            [("company_id", "=", current_company.id)]
        )
        if not mappings:
            raise UserError(_("No mapping found for this company"))
        vals = {}
        for m in mappings:
            value = api_data.get(m.api_key)
            if value:
                field_name = m.partner_field_id.name
                vals[field_name] = value
        return vals

    def update_from_api(self, api_data):
        vals = self.get_mappings_data(api_data)
        if vals:
            self.update(vals)
