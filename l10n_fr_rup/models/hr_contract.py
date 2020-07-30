# -*- coding: utf-8 -*-
# Copyright (C) 2020 Akretion (http://www.akretion.com/)

from openerp import models, fields, api


class HrContract(models.Model):
    _inherit = "hr.contract"
    _order = "date_start,name"

    pcs_id = fields.Many2one("hr.employee.pcs", "PCS")
    employer_address_id = fields.Many2one("res.partner", "Addresse de l'employeur")
    qualification = fields.Char("Qualification")
    work_location = fields.Char("Localisation du bureau")

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        # seems @api.onchange doesn't work if old-style onchange is defined in XML
        result = super(HrContract, self).onchange_employee_id(
            cr, uid, ids, employee_id, context=None
        )
        employee_id = self.pool.get("hr.employee").browse(
            cr, uid, employee_id, context=context
        )
        if employee_id:
            result["value"]["pcs_id"] = employee_id.pcs_id and employee_id.pcs_id.id
            result["value"]["qualification"] = employee_id.qualification
            result["value"]["work_location"] = employee_id.work_location
        else:
            result["value"]["pcs_id"] = False
            result["value"]["qualification"] = False
            result["value"]["work_location"] = False
        return result
