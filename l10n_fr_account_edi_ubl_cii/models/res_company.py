# Copyright 2004-2015 Odoo S.A. (https://odoo.com)
# Copyright 2026 Le Filament (https://le-filament.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
import re

from odoo import api, fields, models
from odoo.exceptions import UserError

PDP_identifier_re = re.compile(r"^([0-9]{9})(_[0-9]{14})?(_.+)?$")


class ResCompany(models.Model):
    _inherit = "res.company"

    pdp_identifier = fields.Char(
        compute="_compute_pdp_identifier",
        inverse="_inverse_pdp_identifier",
        groups="base.group_user",
    )

    @api.depends("partner_id", "partner_id.peppol_eas", "partner_id.peppol_endpoint")
    def _compute_pdp_identifier(self):
        for record in self:
            partner = record.partner_id
            record.pdp_identifier = (
                partner.peppol_endpoint if partner.peppol_eas == "0225" else False
            )

    def _inverse_pdp_identifier(self):
        for record in self:
            if not record.pdp_identifier:
                continue
            match = PDP_identifier_re.match(record.pdp_identifier or "")
            siren = match and match.group(1)
            if not siren:
                raise UserError(
                    self.env._(
                        "The identifier %s is not valid. The expected format "
                        "is: SIREN, SIREN_SIRET, SIREN_SIRET_CodeRoutage or "
                        "SIREN_SuffixeAdressage",
                        record.pdp_identifier,
                    )
                )
            siret = (
                match.group(2)[1:] if match and match.group(2) else False
            )  # Remove `_` at the start
            record.partner_id.write(
                {
                    "peppol_eas": "0225",
                    "peppol_endpoint": record.pdp_identifier,
                    "siret": siret or siren,
                }
            )

    @api.model
    def _check_pdp_identifier(self, pdp_identifier, warning=False):
        return pdp_identifier and PDP_identifier_re.match(pdp_identifier)
