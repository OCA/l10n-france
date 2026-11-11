{
    "name": "France - OCA Chart of Account",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations/Account Charts",
    "summary": "Fork of l10n_fr_account: fewer taxes, ready for FR OCA VAT return",
    "author": "Akretion,Odoo SA,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "countries": ["fr"],
    "icon": "/account/static/description/l10n.png",
    "depends": [
        "account_tax_unece",
        "l10n_fr_account",
    ],
    "data": [
        "views/account_fiscal_position.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "post_init_hook": "_l10n_fr_post_init_hook",
    "license": "LGPL-3",
}
