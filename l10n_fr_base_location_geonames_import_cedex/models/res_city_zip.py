# © 2019 Le Filament (<http://www.le-filament.com>)
# Copyright 2016 Nicolas Bessi, Camptocamp SA
# Copyright 2018 Aitor Bouzas <aitor.bouzas@adaptivecity.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class ScopResCityZip(models.Model):
    _inherit = "res.city.zip"

    cedex = fields.Char("CEDEX")

    _sql_constraints = [
        ('name_city_uniq', 'UNIQUE(name, city_id, cedex)',
         'You already have a zip with that code in the same city. '
         'The zip code must be unique within it\'s city'),
    ]

    @api.multi
    @api.depends('name', 'city_id')
    def _compute_new_display_name(self):
        for rec in self:
            if rec.cedex:
                name = [rec.name, rec.city_id.name, rec.cedex]
            else:
                name = [rec.name, rec.city_id.name]
            if rec.city_id.state_id:
                name.append(rec.city_id.state_id.name)
            if rec.city_id.country_id:
                name.append(rec.city_id.country_id.name)
            rec.display_name = ", ".join(name)
