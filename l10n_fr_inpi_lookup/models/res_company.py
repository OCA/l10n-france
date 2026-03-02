# Copyright 2025 Le Filament (https://le-filament.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    inpi_api_handler_id = fields.Many2one(
        "api.inpi",
        string="Configuration INPI",
    )

    inpi_mapping_ids = fields.One2many(
        "api.inpi.mapping",
        "company_id",
    )

    inpi_user = fields.Char("User")
    inpi_pass = fields.Char("Password")
    inpi_timeout = fields.Integer("API Timeout (s)", default=5)
    inpi_url = fields.Char(default="https://registre-national-entreprises.inpi.fr/api")

    def get_inpi_handler(self):
        if not self.inpi_user or not self.inpi_pass:
            raise UserError(_("Configure INPI access"))
        if not self.inpi_api_handler_id:
            self.inpi_api_handler_id = self.env["api.inpi"].create(
                {
                    "company_id": self.id,
                }
            )
        return self.inpi_api_handler_id

    def action_init_inpi_mapping(self):
        self.ensure_one()
        if not self.inpi_mapping_ids:
            _fields = ["name", "street", "zip", "city", "siren"]
            mapping_vals = []
            for field_name in _fields:
                partner_field = self.env["ir.model.fields"].search(
                    [("model", "=", "res.partner"), ("name", "=", field_name)], limit=1
                )
                if partner_field:
                    mapping_vals.append(
                        {
                            "api_key": field_name,
                            "partner_field_id": partner_field.id,
                            "company_id": self.id,
                        }
                    )
            self.env["api.inpi.mapping"].create(mapping_vals)
