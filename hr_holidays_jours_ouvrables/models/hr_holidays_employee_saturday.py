# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class HrHolidaysEmployeeSaturday(models.Model):
    _name = 'hr.holidays.employee.saturday'
    _description = 'Holidays Saturdays for Employee'

    status_id = fields.Many2one(
        comodel_name='hr.holidays.status',
        string='Leave Type',
        required=True,
    )
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
    )
    saturday = fields.Date(
        string='Saturday Date',
        required=True,
    )
    holidays_id = fields.Many2one(
        comodel_name='hr.holidays',
        string='Leave',
        ondelete='cascade',
    )
