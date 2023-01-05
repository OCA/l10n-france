# © 2022 David BEAL @ Akretion
# © 2022 Alexis DE LATTRE @ Akretion

{
    "name": "Account Factoring Receivable Balance",
    "version": "16.0.2.1.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Akretion",
    "website": "https://github.com/akretion/odoo-factoring",
    "maintainers": [
        "bealdav",
        "alexis-via",
    ],
    "depends": [
        "base_factoring",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/misc.xml",
        "views/subrogation_receipt.xml",
        "views/account_journal.xml",
        "views/company.xml",
    ],
    "demo": [
        "views/company_demo.xml",
    ],
}
