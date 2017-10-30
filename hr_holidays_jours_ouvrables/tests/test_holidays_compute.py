# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

"""

Results checked with:
http://www.efl.fr/simulateurs-SI/decompte-jours-ouvrables-ouvres.html

"""

from odoo import exceptions
from .common import HolidaysComputeCommon


class TestHolidaysWithoutJoursOuvrables(HolidaysComputeCommon):
    """ Test that leaves computation without the option still works """

    def setUp(self):
        super(TestHolidaysWithoutJoursOuvrables, self).setUp()
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
        self.company.holiday_deduct_ouvrable = False

    def test_schedule_holidays(self):
        """ Test holidays when the option is disabled """
        # all working days
        self.assertEqual(5, self._get_days('2017-05-15', '2017-05-19'))
        # 25 is a public holiday
        self.assertEqual(4, self._get_days('2017-05-22', '2017-05-26'))
        # beginning of week
        self.assertEqual(2, self._get_days('2017-05-29', '2017-05-30'))
        # middle of week
        self.assertEqual(3, self._get_days('2017-06-06', '2017-06-08'))
        # end of week
        self.assertEqual(2, self._get_days('2017-06-15', '2017-06-16'))


class TestHolidaysComputeMonToFriWeek(HolidaysComputeCommon):

    def setUp(self):
        super(TestHolidaysComputeMonToFriWeek, self).setUp()
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

    def _record_saturday(self, date):
        self.saturday_model.create({
            'status_id': self.holiday_type.id,
            'employee_id': self.employee.id,
            'saturday': date,
        })

    def test_schedule_week_complete(self):
        """ Schedule from Monday to Sunday without public holiday """
        self.assertEqual(
            6, self._get_days('2017-05-15', '2017-05-21'),
            "5 week days + 1 Saturday expected"
        )

    def test_schedule_work_week_complete(self):
        """ Schedule from Monday to Friday without public holiday """
        self.assertEqual(
            6, self._get_days('2017-05-15', '2017-05-19'),
            "5 week days + 1 Saturday expected"
        )

    def test_schedule_week_public_holiday(self):
        """ Schedule from Monday to Sunday with a public holiday """
        self.assertEqual(
            5, self._get_days('2017-05-22', '2017-05-28'),
            "4 week days + 1 Saturday expected"
        )

    def test_schedule_work_week_public_holiday(self):
        """ Schedule from Monday to Friday with a public holiday """
        self.assertEqual(
            5, self._get_days('2017-05-22', '2017-05-26'),
            "4 week days + 1 Saturday expected"
        )

    def test_schedule_two_weeks(self):
        """ Schedule from Monday to Sunday during 2 weeks + public holiday """
        self.assertEqual(
            11, self._get_days('2017-05-22', '2017-06-04'),
            "9 week days + 2 Saturday expected"
        )

    def test_schedule_week_beginning_of_week(self):
        """ Schedule from Monday to Tuesday """
        self.assertEqual(
            2, self._get_days('2017-05-15', '2017-05-16'),
            "2 week days expected"
        )

    def test_schedule_week_middle_of_week(self):
        """ Schedule from Tuesday to Thursday """
        self.assertEqual(
            3, self._get_days('2017-05-16', '2017-05-18'),
            "3 week days expected"
        )

    def test_schedule_week_end_of_week(self):
        """ Schedule from Thursday to Friday """
        self.assertEqual(
            3, self._get_days('2017-05-18', '2017-05-21'),
            "2 week days + 1 Saturday expected"
        )

    def test_more_than_5_saturdays_at_once(self):
        """ More than 5 saturdays per year in one range """
        self.assertEqual(
            35, self._get_days('2017-08-28', '2017-10-08'),
            "30 week days + 5 Saturdays (capped at 5)"
        )

    def test_more_than_5_saturdays(self):
        """ More than 5 saturdays per year in one range """
        self._record_saturday('2017-01-07')
        self._record_saturday('2017-01-14')
        self._record_saturday('2017-01-21')
        self._record_saturday('2017-01-28')
        self._record_saturday('2017-02-04')
        self.assertEqual(
            30, self._get_days('2017-08-28', '2017-10-08'),
            "30 week days + 0 Saturdays (capped at 5, 5 already existing)"
        )

    def test_more_than_5_saturdays_mixed(self):
        """ More than 5 saturdays per year in one range """
        self._record_saturday('2017-01-07')
        self._record_saturday('2017-01-14')
        self._record_saturday('2017-01-21')
        self.assertEqual(
            32, self._get_days('2017-08-28', '2017-10-08'),
            "30 week days + 2 Saturdays (capped at 5, 3 already existing)"
        )

    def test_saturday_already_in_range(self):
        """ 5 Saturdays with one in the range """
        self._record_saturday('2017-01-07')
        self._record_saturday('2017-01-14')
        self._record_saturday('2017-01-21')
        self._record_saturday('2017-01-28')
        self._record_saturday('2017-09-02')
        self.assertEqual(
            31, self._get_days('2017-08-28', '2017-10-08'),
            "30 week days + 1 Saturdays (capped at 5, 4 already existing)"
        )

    def test_saturdays_cross_year(self):
        """ 3 recorded saturdays in year 1, 3 in year 2 """
        self._record_saturday('2016-07-09')
        self._record_saturday('2016-07-16')
        self._record_saturday('2016-07-23')
        self._record_saturday('2017-06-17')
        self._record_saturday('2017-06-24')
        self._record_saturday('2017-07-01')
        self.assertEqual(
            44, self._get_days('2016-12-05', '2017-01-29'),
            "20x2016 + 20x2017 week days + 2x2016 + 2x2017 Saturdays"
        )

    def test_public_holiday_on_saturday(self):
        """ Saturday falls on a public holiday """
        self.assertEqual(
            5, self._get_days('2017-11-06', '2017-11-12'),
            "5 week days, saturday is a public holiday"
        )


class TestHolidaysComputeOtherWorkingHours(HolidaysComputeCommon):

    def test_schedule_monday_saturday(self):
        """ Cannot compute "Jours Ouvrables" for other work weeks

        Than Monday-Friday.
        """
        # Create a work calendar from Monday to Saturday
        for day in range(1, 6):
            self.calendar_attendance_model.create(
                {
                    'name': 'Attendance',
                    'dayofweek': str(day),
                    'hour_from': '08',
                    'hour_to': '18',
                    'calendar_id': self.calendar.id
                }
            )
        with self.assertRaisesRegexp(
                exceptions.UserError, 'different than Monday-Friday'):
            self._get_days('2017-05-16', '2017-05-21')
