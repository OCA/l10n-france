# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "France VAT Return - Selenium extension",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "Autofill CA3 on impots.gouv.fr via Selenium IDE",
    "development_status": "Beta",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["l10n_fr_account_vat_return"],
    "data": [
        "views/l10n_fr_account_vat_return.xml",
    ],
    "installable": True,
}
