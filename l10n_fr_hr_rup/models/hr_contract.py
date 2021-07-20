# Copyright (C) 2020 Akretion (http://www.akretion.com/)

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"
    _order = "date_start,name"

    employer_address_id = fields.Many2one("res.partner", "Addresse de l'employeur")
    pcs_id = fields.Many2one(
        "hr.employee.pcs", "PCS", compute="_compute_pcs_id", store=True, readonly=False
    )
    qualification = fields.Char(
        "Qualification", compute="_compute_qualification", store=True, readonly=False
    )
    work_location = fields.Char(
        "Localisation du bureau",
        compute="_compute_work_location",
        store=True,
        readonly=False,
    )

    @api.depends("employee_id")
    def _compute_pcs_id(self):
        for rec in self:
            rec.pcs_id = rec.employee_id.pcs_id

    @api.depends("employee_id")
    def _compute_qualification(self):
        for rec in self:
            rec.qualification = rec.employee_id.qualification

    @api.depends("employee_id")
    def _compute_work_location(self):
        for rec in self:
            rec.work_location = rec.employee_id.work_location
