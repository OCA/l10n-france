# Copyright 2021 Camptocamp
#   @author Silvio Gregorini <silvio.gregorini@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class EcotaxeCollector(models.Model):
    _name = "ecotaxe.collector"
    _description = "Ecotaxe collector"

    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner", string="Partner", required=False)
    active = fields.Boolean(default=True)
