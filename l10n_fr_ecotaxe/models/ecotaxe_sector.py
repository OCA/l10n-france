# Copyright 2021 Camptocamp
#   @author Silvio Gregorini <silvio.gregorini@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class EcotaxeSector(models.Model):
    _name = "ecotaxe.sector"
    _description = "Ecotaxe Sector"

    name = fields.Char(required=True)
    description = fields.Char()
    active = fields.Boolean(default=True)
