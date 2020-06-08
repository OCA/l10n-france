# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class AccountConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fr_intrastat_accreditation = fields.Char(
        related='company_id.fr_intrastat_accreditation')
