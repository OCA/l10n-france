# © 2019 Le Filament (https://le-filament.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    cedex = fields.Char("Cedex")
