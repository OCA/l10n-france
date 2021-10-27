# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import TransactionCase


class HolidaysComputeCommon(TransactionCase):

    def setUp(self):
        super(HolidaysComputeCommon, self).setUp()
        self.user = self.env['res.users'].with_context(
            {'no_reset_password': True, 'tracking_disable': True}
        ).create({
            'name': 'test user',
            'login': 'test',
            'email': 'test@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        self.employee_model = self.env['hr.employee']
        self.holiday_status_model = self.env['hr.holidays.status']
        self.public_holiday_model = self.env["hr.holidays.public"]
        self.public_holiday_model_line = self.env["hr.holidays.public.line"]
        self.employee_model = self.env['hr.employee']
        self.calendar_model = self.env['resource.calendar']
        self.calendar_attendance_model = (
            self.env['resource.calendar.attendance']
        )
        self.saturday_model = self.env['hr.holidays.employee.saturday']
        self.holiday_model = self.env['hr.holidays']

        self.company = self.env.ref('base.main_company')
        self.company.holiday_deduct_ouvrable = True
        self.company.holiday_max_number_of_saturday = 5

        # Create employee
        self.employee = self.employee_model.create({
            'name': 'Employee 1',
            'user_id': self.user.id,
        })

        # Create calendar
        self.calendar = self.calendar_model.create({
            'name': 'Calendar'
        })

        # Create some public holidays:
        public_holiday = self.public_holiday_model.create({
            'year': 2017,
        })
        self.public_holiday_model_line.create({
            'name': u'Fête du Travail',
            'date': '2017-05-01',  # Monday
            'year_id': public_holiday.id
        })
        self.public_holiday_model_line.create({
            'name': u'Fête de la Victoire',
            'date': '2017-05-08',  # Monday
            'year_id': public_holiday.id
        })
        self.public_holiday_model_line.create({
            'name': u'Ascension',
            'date': '2017-05-25',  # Thursday
            'year_id': public_holiday.id
        })
        self.public_holiday_model_line.create({
            'name': u'Armistice de 1918',
            'date': '2017-11-11',  # Saturday
            'year_id': public_holiday.id
        })

        # create leave type
        self.holiday_type = self.holiday_status_model.create(
            {
                'name': 'Leave',
                'exclude_public_holidays': True,
                'exclude_rest_days': True,
                'deduct_ouvrable': True,
                'company_id': self.company.id,
            }
        )

    def _get_days(self, date_from, date_to):
        if len(date_from) == 10:
            date_from += ' 08:00:00'
        if len(date_to) == 10:
            date_to += ' 18:00:00'

        leave = self.holiday_model.new({
            'name': 'Holidays',
            'employee_id': self.employee.id,
            'type': 'remove',
            'holiday_type': 'employee',
            'holiday_status_id': self.holiday_type.id,
            'date_from': date_from,
            'date_to': date_to,
        })
        leave._onchange_date_from()
        return leave.number_of_days_temp

    def _create_holidays(self, date_from, date_to):
        return self.holiday_model.sudo(self.user).create({
            'name': 'Holidays',
            'employee_id': self.employee.id,
            'type': 'remove',
            'holiday_type': 'employee',
            'holiday_status_id': self.holiday_type.id,
            'date_from': date_from,
            'date_to': date_to,
        })

    def _search_saturdays(self):
        return self.saturday_model.search(
            [('employee_id', '=', self.employee.id)]
        )
