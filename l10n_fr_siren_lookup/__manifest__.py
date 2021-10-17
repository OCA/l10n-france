# Copyright 2018-2021 Le Filament (<https://le-filament.com>)
# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "SIREN Lookup",
    "summary": "Lookup partner in French SIREN database",
    "version": "14.0.1.0.0",
    "category": "Partner",
    "website": "https://github.com/OCA/l10n-france",
    "author": "Le Filament, Akretion, Odoo Community Association (OCA)",
    "maintainers": ["remi-filament"],
    "license": "AGPL-3",
    "depends": [
        "l10n_fr_siret",
    ],
    "external_dependencies": {"python": ["requests", "stdnum"]},
    "data": [
        "wizard/siren_wizard.xml",
        "views/res_partner.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
}
