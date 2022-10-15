# Copyright 2017-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "L10n FR Account Tax UNECE",
    "summary": "Auto-configure UNECE params on French taxes",
    "version": "14.0.1.1.0",
    "category": "French Localization",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "license": "AGPL-3",
    "depends": ["l10n_fr", "account_tax_unece"],
    "data": ["data/account_tax_template.xml"],
    "post_init_hook": "set_unece_on_taxes",
    "installable": True,
    "auto_installable": True,
}
