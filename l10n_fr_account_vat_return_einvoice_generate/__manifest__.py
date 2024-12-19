# Copyright 2024 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Adapt e-invoice generation to France VAT on payment",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "Glue module between account_einvoice_generate and l10n_fr_account_vat_return",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["account_einvoice_generate", "l10n_fr_account_vat_return"],
    "installable": True,
    "auto_install": True,
}
