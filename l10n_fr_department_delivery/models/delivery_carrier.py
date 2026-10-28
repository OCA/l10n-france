# Copyright 2015-2023 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    department_ids = fields.Many2many("res.country.department", string="Departments")

    unallowed_department_ids = fields.Many2many(
        "res.country.department",
        "delivery_carrier_unallowed_department_rel",
        "carrier_id",
        "department_id",
        string="Unallowed Departments",
    )

    def _match_address(self, partner):
        self.ensure_one()
        res = super()._match_address(partner)
        if not res:
            return res
        if self.department_ids and partner.country_department_id not in self.department_ids:
            return False
        if (
            self.unallowed_department_ids
            and partner.country_department_id in self.unallowed_department_ids
        ):
            return False
        return res
