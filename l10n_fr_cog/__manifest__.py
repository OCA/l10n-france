# Copyright 2020-2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Code Officiel Géographique",
    "summary": "Add Code Officiel Géographique (COG) on countries",
    "version": "17.0.1.0.0",
    "category": "French Localization",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "license": "AGPL-3",
    "depends": ["base"],
    "data": [
        "data/country.xml",
        "views/country.xml",
    ],
    "post_init_hook": "set_fr_cog",
    "installable": True,
}
