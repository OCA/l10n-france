# Copyright 2025 Le Filament (https://le-filament.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    force_vat_siret_lookup = fields.Boolean(
        related="company_id.force_vat_siret_lookup",
        readonly=False,
        string="Force VAT Numbers during SIRET Lookups if VIES check times out "
        "or is disabled",
    )
