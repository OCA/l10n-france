# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestSsnidCheck(TransactionCase):

    def test_validate_ssnid(self):
        heo = self.env['hr.employee']
        with self.assertRaises(ValidationError):
            heo.france_check_ssnid('1 91 12')
        with self.assertRaises(ValidationError):
            heo.france_check_ssnid('1 91 02 99 412 042 19')
        self.assertTrue(heo.france_check_ssnid('1 91 02 99 412 042 42'))
        self.assertTrue(heo.france_check_ssnid('1 55 01 2A 011 222 86'))
