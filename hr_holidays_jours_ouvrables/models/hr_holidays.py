# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import calendar
from datetime import timedelta
from odoo import _, exceptions, api, fields, models


class HrHolidays(models.Model):
    _inherit = 'hr.holidays'

    # technical field used to know if we have to apply the rule: when both
    # company + leave have the option activated
    has_to_deduct_ouvrable = fields.Boolean(
        compute='_compute_has_to_deduct_ouvrable'
    )

    @api.depends('holiday_status_id.deduct_ouvrable',
                 'holiday_status_id.company_id.holiday_deduct_ouvrable')
    def _compute_has_to_deduct_ouvrable(self):
        for record in self:
            if record.type != 'remove':
                continue
            if (record.employee_id.company_id.holiday_deduct_ouvrable and
                    record.holiday_status_id.deduct_ouvrable):
                record.has_to_deduct_ouvrable = True

    def _recompute_number_of_days(self):
        days = super(HrHolidays, self)._recompute_number_of_days()
        if not days:
            return days
        supported_calendars = [
            range(5),  # Monday to Friday
        ]
        contract = self.employee_id.contract_id
        resource_weekdays = contract.working_hours.get_weekdays()
        if (self.has_to_deduct_ouvrable and
                resource_weekdays not in supported_calendars):
            raise exceptions.UserError(
                _('Using a "Jours Ouvrables" calendar status is not possible '
                  'with a work week different than Monday-Friday')
            )
        elif self.has_to_deduct_ouvrable:
            saturdays = self._get_deducted_saturdays()
            days = days + len(saturdays)
            self.number_of_days = days
        return days

    @staticmethod
    def _iter_between_dates(start, end):
        dates = [start + timedelta(days=d)
                 for d in range((end - start).days + 1)]
        for date in dates:
            yield date

    def _get_deducted_saturdays(self):
        public_holiday_model = self.env['hr.holidays.public']
        saturday_model = self.env['hr.holidays.employee.saturday']

        start = fields.Datetime.from_string(self.date_from)
        end = fields.Datetime.from_string(self.date_to)
        employee = self.employee_id
        is_public_holiday = public_holiday_model.is_public_holiday
        limit = employee.company_id.holiday_max_number_of_saturday

        # use dict with keys per years so we can count how many saturday we
        # have over the period and ensure we don't add more saturdays than the
        # limit
        current_saturdays = {}
        recorded_saturdays = {}
        for year in range(start.year, end.year + 1):
            # search recorded saturdays for each year touched by holidays
            recorded_saturdays[year] = saturday_model.search(
                [('employee_id', '=', employee.id),
                 ('saturday', '>=', '%s-01-01' % year),
                 ('saturday', '<=', '%s-12-31' % year),
                 # exclude the saturdays recorded in
                 # the same range, we recompute them
                 '|', ('saturday', '<', start), ('saturday', '>', end),
                 ]
            )

        for date in self._iter_between_dates(start, end):
            # we look for fridays in leaves, so it works when
            # users set leaves from monday to friday too
            if date.weekday() == calendar.FRIDAY:
                saturday = date + timedelta(days=1)
                if is_public_holiday(saturday, employee_id=employee.id):
                    continue
                year = date.year
                current_saturdays.setdefault(year, [])

                other_saturdays = recorded_saturdays[year]
                current = current_saturdays[year]
                if len(other_saturdays) + len(current) < limit:
                    current.append(saturday)

        return [sat for years in current_saturdays.values() for sat in years]

    @api.model
    def create(self, vals):
        record = super(HrHolidays, self).create(vals)
        if record.has_to_deduct_ouvrable:
            saturdays = record._get_deducted_saturdays()
            record._sync_employee_saturdays(saturdays)
        return record

    @api.multi
    def write(self, vals):
        result = super(HrHolidays, self).write(vals)
        for record in self:
            if record.has_to_deduct_ouvrable:
                saturdays = record._get_deducted_saturdays()
                record._sync_employee_saturdays(saturdays)
        return result

    @api.multi
    def _sync_employee_saturdays(self, saturdays):
        # remove linked saturdays if dates of holidays have been changed
        saturday_model = self.env['hr.holidays.employee.saturday'].sudo()
        saturday_dates = [fields.Date.to_string(sat) for sat in saturdays]
        saturday_model.search(
            [('saturday', 'not in', saturday_dates),
             ('holidays_id', '=', self.id),
             ]
        ).unlink()

        for saturday in saturdays:
            record = saturday_model.search(
                [('holidays_id', '=', self.id),
                 ('saturday', '=', saturday),
                 ])
            if record:
                record.write({
                    'status_id': self.holiday_status_id.id,
                    'employee_id': self.employee_id.id,
                })
            else:
                saturday_model.create({
                    'status_id': self.holiday_status_id.id,
                    'employee_id': self.employee_id.id,
                    'saturday': saturday,
                    'holidays_id': self.id,
                })
