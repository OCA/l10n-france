# Copyright 2020-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    fr_das2_partner_declare_threshold = fields.Integer(
        string="DAS2 Partner Declaration Threshold", default=1200
    )

    _sql_constraints = [
        (
            "fr_das2_partner_declare_threshold_positive",
            "CHECK(fr_das2_partner_declare_threshold >= 0)",
            "The DAS2 partner declaration threshold must be positive!",
        )
    ]
