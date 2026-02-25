# Copyright 2025 Le Filament (https://le-filament.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ApiPartnerMapping(models.Model):
    _name = "api.inpi.mapping"
    _description = "Mapping API INPI vers Partner"

    api_key = fields.Selection(
        [
            ("name", "Nom / Raison Sociale"),
            ("street", "Rue"),
            ("zip", "Code Postal"),
            ("city", "Ville"),
            ("country_id", "Pays"),
            ("siren", "SIREN"),
            ("siret", "SIRET"),
            ("creation_date", "Date de création"),
            ("ape", "Code APE"),
            ("legal_type", "Forme Juridique"),
            ("staff", "Effectif"),
        ],
        string="Donnée API",
        required=True,
    )

    partner_field_id = fields.Many2one(
        "ir.model.fields",
        string="Champ Odoo Cible",
        domain="[('model', '=', 'res.partner'), "
        "('ttype', 'not in', ['one2many', 'many2many'])]",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one("res.company", string="Société")
