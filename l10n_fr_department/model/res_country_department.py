# Copyright 2013-2022 GRAP (http://www.grap.coop)
# Copyright 2015-2022 Akretion France (http://www.akretion.com)
# @author Sylvain LE GAL (https://twitter.com/legalsylvain)
# @author Alexis de Lattre (alexis.delattre@akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResCountryDepartment(models.Model):
    _description = "Department"
    _name = "res.country.department"
    _order = "country_id, code"
    _rec_names_search = ["name", "code"]

    state_id = fields.Many2one(
        "res.country.state",
        required=True,
    )
    country_id = fields.Many2one(
        "res.country",
        related="state_id.country_id",
        store=True,
    )
    name = fields.Char(string="Department Name", size=128, required=True)
    code = fields.Char(
        string="Department Code",
        size=3,
        required=True,
        help="The department code (ISO 3166-2 codification)",
    )

    _sql_constraints = [
        (
            "code_country_uniq",
            "unique (code, country_id)",
            "You cannot have two departments with the same code in the same country!",
        )
    ]

    @api.depends("name", "code")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} ({rec.code})"
