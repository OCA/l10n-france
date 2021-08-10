# Copyright 2014-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Balance EBP CSV export",
    "version": "14.0.1.0.1",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "development_status": "Alpha",
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["account_financial_report"],
    "data": [
        "report.xml",
        "report/balance_ebp_csv.xml",
        "wizard/trial_balance_wizard_view.xml",
    ],
    "installable": True,
}
