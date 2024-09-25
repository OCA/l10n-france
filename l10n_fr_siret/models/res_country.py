# Copyright 2024 Foodles (https://www.foodles.co/).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo import fields, models


class ResCountry(models.Model):
    _inherit = "res.country"

    show_siret_fields = fields.Boolean(default=True)
