# Copyright (C) 2020 Akretion (http://www.akretion.com/)

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"
    _order = "date_start,name"

    pcs_id = fields.Many2one("hr.employee.pcs", "PCS")
    employer_address_id = fields.Many2one("res.partner", "Addresse de l'employeur")
    qualification = fields.Char("Qualification")
    work_location = fields.Char("Localisation du bureau")

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        super()._onchange_employee_id()
        self.pcs_id = self.employee_id.pcs_id
        self.qualification = self.employee_id.qualification
        self.work_location = self.employee_id.work_location
