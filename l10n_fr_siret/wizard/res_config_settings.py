from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    fr_siret_dup_check = fields.Selection(
        related="company_id.fr_siret_dup_check", readonly=False
    )
