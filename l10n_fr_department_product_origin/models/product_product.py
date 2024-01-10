# Copyright (C) 2012 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# @author Julien WESTE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"

    department_id = fields.Many2one(
        comodel_name="res.country.department",
        string="Department of Origin",
        ondelete="restrict",
    )

    department_id_domain = fields.Binary(
        compute="_compute_department_id_domain",
        help="Technical field, used to compute dynamically department domain"
        " depending on the state.",
    )

    @api.constrains("state_id", "department_id")
    def _check_state_id_department_id(self):
        for product in self.filtered(lambda x: x.state_id and x.department_id):
            if product.state_id != product.department_id.state_id:
                raise ValidationError(
                    _(
                        "The department '%(department_name)s' doesn't belong to"
                        " the state '%(state_name)s'",
                        department_name=product.department_id.name,
                        state_name=product.state_id.name,
                    )
                )

    @api.onchange("state_id")
    def onchange_state_id(self):
        if self.department_id and self.department_id.state_id != self.state_id:
            self.department_id = False
        return super().onchange_state_id()

    @api.onchange("department_id")
    def onchange_department_id(self):
        if self.department_id:
            self.state_id = self.department_id.state_id

    @api.depends("country_id", "state_id")
    def _compute_department_id_domain(self):
        for product in self.filtered(lambda x: x.state_id):
            product.department_id_domain = [("state_id", "=", product.state_id.id)]
        for product in self.filtered(lambda x: not x.state_id and x.country_id):
            product.department_id_domain = [
                ("state_id", "in", product.country_id.state_ids)
            ]
        for product in self.filtered(lambda x: not x.state_id and not x.country_id):
            product.department_id_domain = []
