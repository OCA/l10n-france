# Copyright 2018-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Factur-X Invoices Import for France",
    "version": "14.0.1.0.2",
    "category": "Localisation",
    "license": "AGPL-3",
    "summary": "France-specific module to import Factur-X invoices",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": [
        "account_invoice_import_facturx",
        "l10n_fr_business_document_import",
    ],
    "auto_install": True,
    "installable": True,
}
