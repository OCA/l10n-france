# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _, api, exceptions, fields, models


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

    _sql_constraints = [
        ('saturday_uniq', 'unique (employee_id, saturday)',
         "This saturday is already used."),
    ]

    @api.constrains('holidays_id', 'saturday')
    def _check_saturday_in_holidays(self):
        for record in self:
            if not record.holidays_id:
                continue
            saturday = fields.Date.from_string(record.saturday)
            start = fields.Date.from_string(record.holidays_id.date_from)
            end = fields.Date.from_string(record.holidays_id.date_to)
            if not (start < saturday < end):
                raise exceptions.ValidationError(
                    _('The date of this saturday is not within the '
                      'leave bounds.')
                )
