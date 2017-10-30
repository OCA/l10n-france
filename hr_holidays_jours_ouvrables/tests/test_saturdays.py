# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from datetime import datetime
from psycopg2 import IntegrityError

from odoo import exceptions
from odoo.tools import mute_logger
from odoo.tests.common import TransactionCase
from .common import HolidaysComputeCommon


class TestIterDates(TransactionCase):

    def test_iter_dates(self):
        holidays_model = self.env['hr.holidays']
        start = datetime(2017, 5, 15)
        end = datetime(2017, 5, 19)
        self.assertEqual(
            [datetime(2017, 5, 15), datetime(2017, 5, 16),
             datetime(2017, 5, 17), datetime(2017, 5, 18),
             datetime(2017, 5, 19),
             ],
            list(holidays_model._iter_between_dates(start, end))
        )


class TestSaturdaySync(HolidaysComputeCommon):

    def setUp(self):
        super(TestSaturdaySync, self).setUp()
        # Create a work calendar from Monday to Friday
        for day in range(5):
            self.calendar_attendance_model.create(
                {
                    'name': 'Attendance',
                    'dayofweek': str(day),
                    'hour_from': '08',
                    'hour_to': '18',
                    'calendar_id': self.calendar.id
                }
            )

    def test_create_saturdays(self):
        """ Saturdays are recorded """
        self._create_holidays('2017-08-28', '2017-10-08')
        saturdays = self._search_saturdays()
        self.assertItemsEqual(
            ['2017-09-02', '2017-09-09', '2017-09-16',
             '2017-09-23', '2017-09-30'],
            saturdays.mapped('saturday')
        )

    def test_create_saturdays_limit(self):
        """ Recorded saturday respect the limit """
        self._create_holidays('2017-08-28', '2017-12-08')
        saturdays = self._search_saturdays()
        self.assertItemsEqual(
            ['2017-09-02', '2017-09-09', '2017-09-16',
             '2017-09-23', '2017-09-30'],
            saturdays.mapped('saturday'),
            "Must not have more than 5 saturdays as per limit"
        )

    def test_create_saturday_values(self):
        """ Saturdays are recorded with proper values """
        leave = self._create_holidays('2017-06-19', '2017-06-25')
        saturdays = self._search_saturdays()
        self.assertEqual(1, len(saturdays))
        self.assertEqual('2017-06-24', saturdays.saturday)
        self.assertEqual(self.holiday_type, saturdays.status_id)
        self.assertEqual(leave, saturdays.holidays_id)

    def test_update_saturdays(self):
        """ Saturdays are updated with proper values """
        leave = self._create_holidays('2017-06-19', '2017-06-25')
        saturdays = self._search_saturdays()
        self.assertEqual(1, len(saturdays))
        self.assertEqual(self.holiday_type, saturdays.status_id)
        holiday_type_2 = self.holiday_status_model.create(
            {'name': 'Leave',
             'exclude_public_holidays': True,
             'exclude_rest_days': True,
             'deduct_ouvrable': True,
             'company_id': self.company.id,
             }
        )
        leave.holiday_status_id = holiday_type_2
        self.assertEqual(1, len(saturdays))
        self.assertEqual(holiday_type_2, saturdays.status_id)

    def test_unlink_saturdays(self):
        """ Recorded Saturdays no more in range are removed """
        leave = self._create_holidays('2017-08-28', '2017-10-08')
        saturdays = self._search_saturdays()
        self.assertItemsEqual(
            ['2017-09-02', '2017-09-09', '2017-09-16',
             '2017-09-23', '2017-09-30'],
            saturdays.mapped('saturday')
        )
        leave.date_to = '2017-09-17'
        saturdays = self._search_saturdays()
        self.assertItemsEqual(
            ['2017-09-02', '2017-09-09', '2017-09-16'],
            saturdays.mapped('saturday')
        )


class SaturdaysChecks(HolidaysComputeCommon):

    def setUp(self):
        super(SaturdaysChecks, self).setUp()
        # Create a work calendar from Monday to Friday
        for day in range(5):
            self.calendar_attendance_model.create(
                {
                    'name': 'Attendance',
                    'dayofweek': str(day),
                    'hour_from': '08',
                    'hour_to': '18',
                    'calendar_id': self.calendar.id
                }
            )

    @mute_logger('odoo.sql_db')
    def test_unique(self):
        self.saturday_model.create({
            'status_id': self.holiday_type.id,
            'employee_id': self.employee.id,
            'saturday': '2017-05-27',
        })
        msg = ('duplicate key value violates unique constraint '
               '"hr_holidays_employee_saturday_saturday_uniq"')
        with self.assertRaisesRegexp(IntegrityError, msg):
            self.saturday_model.create({
                'status_id': self.holiday_type.id,
                'employee_id': self.employee.id,
                'saturday': '2017-05-27',
            })

    def test_saturday_not_in_bounds(self):
        holiday = self._create_holidays('2017-08-28', '2017-8-29')
        msg = 'The date of this saturday is not within the leave bounds'
        with self.assertRaisesRegexp(exceptions.ValidationError, msg):
            self.saturday_model.create({
                'status_id': self.holiday_type.id,
                'employee_id': self.employee.id,
                'saturday': '2017-05-27',
                'holidays_id': holiday.id,
            })
