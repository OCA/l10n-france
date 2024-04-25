# Copyright 2018-2022 Le Filament (<http://www.le-filament.com>)
# Copyright 2021-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FrSiretLookup(models.TransientModel):
    _name = "fr.siret.lookup"
    _description = "Get values from companies"

    name = fields.Char(string="Name to Search", required=True)
    line_ids = fields.One2many("fr.siret.lookup.line", "wizard_id", string="Results")
    partner_id = fields.Many2one("res.partner", required=True)

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
                    _("Partner '%s' is not a company. This action is not relevant.")
                    % partner.display_name
                )
            res.update(
                {
                    "name": partner.name,
                    "partner_id": partner.id,
                }
            )
        return res

    # Action
    @api.model
    def _prepare_partner_from_data(self, data):
        country_id = zipcode = False
        zipcode = data.get("codepostaletablissement")
        if isinstance(zipcode, int):
            zipcode = str(zipcode)
        if zipcode:
            zipcode = zipcode.zfill(5)
            country_id = self.env["res.partner"]._opendatasoft_compute_country(zipcode)
        return {
            "name": data.get("denominationunitelegale")
            or data.get("l1_adressage_unitelegale"),
            "street": data.get("adresseetablissement"),
            "zip": zipcode,
            "city": data.get("libellecommuneetablissement"),
            "country_id": country_id,
            "siren": data.get("siren") and str(data["siren"]) or False,
            "siret": data.get("siret") and str(data["siret"]) or False,
            "category": data.get("categorieentreprise"),
            "creation_date": data.get("datecreationunitelegale"),
            "ape": data.get("activiteprincipaleunitelegale"),
            "ape_label": data.get("divisionunitelegale"),
            "legal_type": data.get("naturejuridiqueunitelegale"),
            "staff": data.get("trancheeffectifsunitelegale", 0),
        }

    def get_lines(self):
        self.ensure_one()
        self.line_ids.unlink()
        # Get request
        res_json = self.env["res.partner"]._opendatasoft_get_raw_data(
            self.name, raise_if_fail=True, rows=30
        )
        # Fill new company lines
        companies_vals = []
        for company in res_json["records"]:
            res = self._prepare_partner_from_data(company["fields"])
            companies_vals.append((0, 0, res))
        self.line_ids = companies_vals
        return {
            "context": self.env.context,
            "view_mode": "form",
            "res_model": self._name,
            "res_id": self.id,
            "view_id": False,
            "type": "ir.actions.act_window",
            "target": "new",
        }


class FrSiretLookupLine(models.TransientModel):
    _name = "fr.siret.lookup.line"
    _description = "Company Selection"

    wizard_id = fields.Many2one("fr.siret.lookup", string="Wizard", ondelete="cascade")
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

    def _prepare_partner_values(self):
        self.ensure_one()
        vat = self.env["res.partner"]._siren2vat_vies(self.siren, raise_if_fail=True)
        vals = {
            "name": self.name,
            "street": self.street,
            "zip": self.zip,
            "city": self.city,
            "country_id": self.country_id.id or False,
            "siret": self.siret,
            "vat": vat,
        }
        return vals

    def update_partner(self):
        self.ensure_one()
        partner = self.wizard_id.partner_id
        partner.write(self._prepare_partner_values())
        partner.message_post(body=_("Partner updated via the opendatasoft.com API."))
