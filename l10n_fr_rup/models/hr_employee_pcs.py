# -*- coding: utf-8 -*-
# Copyright (C) 2020 Akretion (http://www.akretion.com/)

from openerp import models, fields


class HrEmployeePcs(models.Model):
    _name = "hr.employee.pcs"

    name = fields.Char(string="Nom")
