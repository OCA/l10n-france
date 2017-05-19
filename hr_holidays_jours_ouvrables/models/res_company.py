# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    holiday_deduct_ouvrable = fields.Boolean(
        string='Deduct Leaves on "Jours ouvrables"',
        default=False,
    )
    holiday_max_number_of_saturday = fields.Integer(
        string="Max. number of Saturday Holidays",
        default=5,
    )
