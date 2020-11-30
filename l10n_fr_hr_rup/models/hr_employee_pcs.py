# Copyright (C) 2020 Akretion (http://www.akretion.com/)

from odoo import models, fields


class HrEmployeePcs(models.Model):
    _name = "hr.employee.pcs"
    _description = "Hr Employee PCS"

    name = fields.Char(string="Nom")
