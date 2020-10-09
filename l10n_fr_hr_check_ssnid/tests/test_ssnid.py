# Copyright 2018-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSsnidCheck(TransactionCase):
    def test_validate_ssnid(self):
        heo = self.env["hr.employee"]
        # Set company to France
        self.env.user.company_id.country_id = self.env.ref("base.fr").id
        with self.assertRaises(ValidationError):
            heo.create({"name": "AA", "ssnid": "1 91 12"})
        with self.assertRaises(ValidationError):
            heo.create({"name": "AB", "ssnid": "1 91 02 99 412 042 19"})
        heo.create({"name": "AC", "ssnid": "1 91 02 99 412 042 42"})
        heo.create({"name": "AD", "ssnid": "1 55 01 2A 011 222 86"})
