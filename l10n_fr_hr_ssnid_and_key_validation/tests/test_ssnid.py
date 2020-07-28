# -*- coding: utf-8 -*-
# Copyright 2020 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestSsnidAndSsnidKeyCheck(TransactionCase):

    def test_ssnid_ssnid_key(self):
        emp = self.env['hr.employee']
        self.env.user.company_id.country_id = self.env.ref('base.fr').id
        with self.assertRaises(ValidationError):
            emp.create({'name': 'AA', 'ssnid': '19112', 'ssnid_key': '12'})
        with self.assertRaises(ValidationError):
            emp.create({'name': 'AB', 'ssnid': '191029941204219', 'ssnid_key': '12'})
        with self.assertRaises(ValidationError):
            emp.create({'name': 'AB', 'ssnid': '191029941204219', 'ssnid_key': '12'})
        with self.assertRaises(ValidationError):
            emp.create({'name': 'AB', 'ssnid': '1910299412042', 'ssnid_key': '12'})
        emp.create({'name': 'AB', 'ssnid': '1910299412042', 'ssnid_key': '42'})
        emp.create({'name': 'AB', 'ssnid': '155012A011222', 'ssnid_key': '86'})
