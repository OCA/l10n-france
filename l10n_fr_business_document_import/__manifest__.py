# Copyright 2015-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "L10n FR Business Document Import",
    "version": "14.0.1.0.0",
    "category": "French Localization",
    "license": "AGPL-3",
    "summary": "Adapt the module base_business_document_import for France",
    "author": "Akretion,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["l10n_fr_siret", "base_business_document_import"],
    "external_dependencies": {"python": ["python-stdnum"]},
    "installable": True,
    "auto_install": True,
}
