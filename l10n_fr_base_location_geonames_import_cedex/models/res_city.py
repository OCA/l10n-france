# © 2019 Le Filament (<http://www.le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class ScopResCity(models.Model):
    _inherit = "res.city"

    cedex = fields.Char("CEDEX")
