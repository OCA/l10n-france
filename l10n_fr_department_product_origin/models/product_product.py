# Copyright (C) 2012 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# @author Julien WESTE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import Warning as UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    department_id = fields.Many2one(
        comodel_name="res.country.department",
        string="Department",
        help="Department of production of the product",
    )

    # Constrains section
    @api.multi
    @api.constrains("state_id", "department_id")
    def _check_origin_state_country(self):
        for product in self.filtered(lambda x: x.department_id and x.state_id):
            if product.department_id.state_id != product.state_id:
                raise UserError(_("Department must belong to the state."))

    # Onchange section
    @api.onchange("department_id")
    def onchange_department_id(self):
        if self.department_id:
            self.state_id = self.department_id.state_id

    @api.onchange("state_id")
    def onchange_state_id(self):
        if self.department_id and self.department_id.state_id != self.state_id:
            self.department_id = False
        super().onchange_state_id()
