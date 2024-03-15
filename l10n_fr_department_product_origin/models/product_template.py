# Copyright (C) 2012 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# @author Julien WESTE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    department_id = fields.Many2one(
        comodel_name="res.country.department",
        string="Department of Origin",
        compute="_compute_department_id",
        inverse="_inverse_department_id",
        store=True,
    )

    department_id_domain = fields.Binary(
        compute="_compute_department_id_domain",
        help="Technical field, used to compute dynamically department domain"
        " depending on the state.",
    )

    @api.constrains("state_id", "department_id")
    def _check_state_id_department_id(self):
        for template in self.filtered(lambda x: x.department_id and x.state_id):
            if template.state_id != template.department_id.state_id:
                raise ValidationError(
                    _(
                        "The department '%(department_name)s' doesn't belong to"
                        " the state '%(state_name)s'",
                        department_name=template.department_id.name,
                        state_name=template.state_id.name,
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
        for template in self.filtered(lambda x: x.state_id):
            template.department_id_domain = [("state_id", "=", template.state_id.id)]
        for template in self.filtered(lambda x: not x.state_id and x.country_id):
            template.department_id_domain = [
                ("state_id", "in", template.country_id.state_ids.ids)
            ]
        for template in self.filtered(lambda x: not x.state_id and not x.country_id):
            template.department_id_domain = []

    @api.depends("product_variant_ids", "product_variant_ids.department_id")
    def _compute_department_id(self):
        for template in self:
            if template.product_variant_count == 1:
                template.department_id = template.product_variant_ids.department_id
            else:
                template.department_id = False

    def _inverse_department_id(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.state_id = template.state_id

    def _get_related_fields_variant_template(self):
        res = super()._get_related_fields_variant_template()
        res += ["department_id"]
        return res
