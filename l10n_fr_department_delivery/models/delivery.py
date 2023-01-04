# Copyright 2015-2018 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    department_ids = fields.Many2many("res.country.department", string="Departments")

    def filter_carrier_with_departments(self, contact):
        if not contact:
            contact = self.env["res.partner"]
        for carrier in self:
            if (
                carrier.department_ids
                and contact.department_id.id not in carrier.department_ids.ids
            ):
                self -= carrier
        return self
