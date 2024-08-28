# © 2024 Open Source Integrators, Daniel Reis
{
    "name": "Account Factoring for FactoFrance",
    "version": "17.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/l10n-france",
    "author": "Open Source Integrators,Odoo Community Association (OCA)",
    "maintainers": ["dreispt"],
    "depends": [
        "account_factoring_receivable_balance",
        "l10n_fr",
    ],
    "data": [
        "data/subrogation_seq.xml",
        "views/account_journal.xml",
        "views/subrogation_receipt_views.xml",
    ],
    "external_dependencies": {"python": ["unidecode"]},
}
