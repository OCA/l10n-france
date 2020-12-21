# Copyright (C) 2020 Akretion (http://www.akretion.com/)

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    pcs_id = fields.Many2one("hr.employee.pcs", string="PCS")
    qualification = fields.Char("Qualification")
