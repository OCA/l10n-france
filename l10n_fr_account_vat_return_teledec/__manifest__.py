# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "VAT Teletransmission via Teledec.fr",
    "version": "14.0.1.1.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "Teletransmit CA3 via Teledec.fr (subscription required)",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["l10n_fr_account_vat_return"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "wizards/res_config_settings.xml",
        "views/l10n_fr_account_vat_return.xml",
    ],
    "installable": True,
}
