# Copyright 2018-2022 Le Filament (<https://le-filament.com>)
# Copyright 2021-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "SIRET Lookup",
    "summary": "Lookup partner via an API on the SIRENE directory",
    "version": "16.0.1.0.0",
    "category": "Partner",
    "website": "https://github.com/OCA/l10n-france",
    "author": "Le Filament, Akretion, Odoo Community Association (OCA)",
    "maintainers": ["remi-filament", "alexis-via"],
    "license": "AGPL-3",
    "depends": [
        "l10n_fr_siret",
    ],
    "external_dependencies": {"python": ["requests", "python-stdnum>=1.18"]},
    "data": [
        "wizard/fr_siret_lookup_view.xml",
        "views/res_partner.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
}
