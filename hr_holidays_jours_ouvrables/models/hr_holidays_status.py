# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class HrHolidaysStatus(models.Model):
    _inherit = 'hr.holidays.status'

    company_has_deduct_ouvrable = fields.Boolean(
        related='company_id.holiday_deduct_ouvrable',
        readonly=True,
    )
    deduct_ouvrable = fields.Boolean(
        string='Deduct Leaves on "Jours ouvrables"',
        default=False,
    )
