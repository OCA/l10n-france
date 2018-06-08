# -*- coding: utf-8 -*-
# Copyright 2015-2018 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    department_ids = fields.Many2many(
        'res.country.department', string="Departments")

    @api.multi
    def verify_carrier(self, contact):
        self.ensure_one()
        res = super(DeliveryCarrier, self).verify_carrier(contact)
        if (
                self.department_ids and
                contact.department_id and
                contact.department_id not in self.self.department_ids):
            return False
        return res
