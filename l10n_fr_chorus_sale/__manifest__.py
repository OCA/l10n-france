# Copyright 2017-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "L10n FR Chorus Sale",
    "summary": "Add checks on sale orders for Chorus Pro",
    "version": "15.0.1.0.0",
    "category": "French Localization",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "license": "AGPL-3",
    "depends": ["l10n_fr_chorus_account", "sale"],
    "data": ["views/sale_order.xml"],
    "installable": True,
    "auto_install": True,
}
