# Copyright (C) 2012 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# @author Julien WESTE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

from .product_product import ProductProduct


class ProductTemplate(models.Model):
    _inherit = "product.template"

    department_id = fields.Many2one(
        comodel_name="res.country.department",
        string="Department",
        related="product_variant_ids.department_id",
        help="Department of production of the product",
        readonly=False,
    )

    # Onchange section
    @api.onchange("department_id")
    def onchange_department_id(self):
        ProductProduct.onchange_department_id(self)

    @api.onchange("state_id")
    def onchange_state_id(self):
        # We can not share the code between product and template
        # because the call of super is failing
        if self.department_id and self.department_id.state_id != self.state_id:
            self.department_id = False
        super().onchange_state_id()
