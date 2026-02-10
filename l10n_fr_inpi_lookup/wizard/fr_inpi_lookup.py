# Copyright 2018-2022 Le Filament (<http://www.le-filament.com>)
# Copyright 2021-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError


class FrInpiLookup(models.TransientModel):
    _name = "fr.inpi.lookup"
    _description = "Get values from companies"

    name = fields.Char(string="Name to Search", required=True)
    line_ids = fields.One2many(
        "fr.inpi.lookup.line", "wizard_id", string="Results", readonly=True
    )
    partner_id = fields.Many2one("res.partner", readonly=True, required=True)
    with_natural_personne = fields.Boolean("Add natural person", default=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if (
            self.env.context.get("active_id")
            and self.env.context.get("active_model") == "res.partner"
        ):
            partner = self.env["res.partner"].browse(self.env.context["active_id"])
            if not partner.is_company:
                raise UserError(
                    self.env._(
                        f"Partner {partner.display_name} is not a company. "
                        "This action is not relevant."
                    )
                )
            res.update(
                {
                    "name": partner.name,
                    "partner_id": partner.id,
                }
            )
        return res

    def inpi_get_lines(self):
        self.ensure_one()
        self.line_ids.unlink()

        inpi_handler = self.env["api.inpi"].get_handler()
        companies = inpi_handler.get_data_by_name(self.name, rows=30)
        companies_vals = []
        for company in companies:
            res = inpi_handler.inpi_prepare_partner_from_data(
                company,
                with_natural_person=self.with_natural_personne,
            )
            if res:
                companies_vals.append((0, 0, res))

        self.line_ids = companies_vals
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": self._name,
            "res_id": self.id,
            "target": "new",
            "context": self.env.context,
        }


class FrInpiLookupLine(models.TransientModel):
    _name = "fr.inpi.lookup.line"
    _description = "Company Selection"

    wizard_id = fields.Many2one("fr.inpi.lookup", string="Wizard", ondelete="cascade")
    name = fields.Char()
    street = fields.Char()
    zip = fields.Char()
    city = fields.Char()
    country_id = fields.Many2one("res.country", string="Country")
    legal_type = fields.Char()
    siren = fields.Char("SIREN")
    siret = fields.Char("SIRET")
    ape = fields.Char("APE Code")
    ape_label = fields.Char("APE Label")
    creation_date = fields.Date()
    staff = fields.Char("# Staff")
    category = fields.Char()
    active = fields.Boolean()

    def _prepare_partner_values(self):
        self.ensure_one()
        vat, vies_valid = self.env["res.partner"]._siren2vat_vies(
            self.siren, raise_if_fail=True
        )
        vals = {
            "name": self.name,
            "street": self.street,
            "zip": self.zip,
            "city": self.city,
            "country_id": self.country_id.id or False,
            "siret": self.siret,
            "vat": vat,
            "vies_valid": vies_valid,
        }
        return vals

    def update_partner(self):
        self.ensure_one()
        partner = self.wizard_id.partner_id
        partner.write(self._prepare_partner_values())
        partner.message_post(body=self.env._("Partner updated via the INPI API."))
