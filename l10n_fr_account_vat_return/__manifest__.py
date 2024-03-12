# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "France VAT Return",
    "version": "16.0.3.2.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "VAT return for France: CA3, 3310-A, 3519",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["l10n_fr", "l10n_fr_oca", "intrastat_base"],
    "external_dependencies": {"python": ["pypdf>=3.1.0"]},
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "wizards/l10n_fr_vat_exigibility_update_view.xml",
        "wizards/res_config_settings.xml",
        "wizards/l10n_fr_account_vat_return_reimbursement_view.xml",
        "wizards/l10n_fr_vat_draft_move_option_view.xml",
        "views/l10n_fr_account_vat_box.xml",
        "views/l10n_fr_account_vat_return.xml",
        "views/account_fiscal_position.xml",
        "views/account_fiscal_position_template.xml",
        "views/account_tax.xml",
        "views/account_move.xml",
        "data/l10n.fr.account.vat.box.csv",
        "data/account_fiscal_position_template.xml",
    ],
    "installable": True,
}
