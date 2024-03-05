# Copyright 2017-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Factur-X Invoices for France",
    "version": "17.0.1.0.0",
    "category": "Localisation",
    "license": "AGPL-3",
    "summary": "France-specific module to generate Factur-X invoices",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": [
        "account_invoice_facturx",
        "l10n_fr_siret",
    ],
    "auto_install": True,
    "installable": True,
}
