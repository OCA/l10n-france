# © 2022 David BEAL @ Akretion
# © 2022 Alexis DE LATTRE @ Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models


logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bpce_factor_code = fields.Char(related="company_id.bpce_factor_code")
    bpce_start_date = fields.Date(related="company_id.bpce_start_date")
