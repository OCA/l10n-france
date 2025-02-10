# Copyright 2025-Today: GRAP (http://www.grap.coop/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    country_department_id = fields.Many2one(
        comodel_name="res.country.department",
        related="partner_id.country_department_id",
        store=True,
    )
