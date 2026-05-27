# Copyright 2024 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "French localization - SIRET and Accounting",
    "summary": "Glue module between l10n_fr_siret and account",
    "version": "18.0.1.1.0",
    "category": "French Localization",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "license": "AGPL-3",
    "depends": ["l10n_fr_siret", "l10n_fr_account"],
    "data": [
        "views/res_partner.xml",
    ],
    "installable": True,
    "auto_install": True,
    "development_status": "Mature",
}
