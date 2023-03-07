{
    "name": "France - OCA Chart of Account",
    "version": "16.0.1.0.0",
    "category": "Accounting/Localizations/Account Charts",
    "summary": "Fork of l10n_fr: fewer taxes, ready for OCA VAT return for France",
    "author": "Akretion,Odoo SA,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": [
        "account_tax_unece",
    ],
    "data": [
        "data/l10n_fr_chart_data.xml",
        "data/account.account.template.csv",
        "data/account.group.template.csv",
        "data/account_chart_template_data.xml",
        "data/account_data.xml",
        "data/account_tax_data.xml",
        "data/account_account_template_default_tax.xml",
        "data/account_fiscal_position_template_data.xml",
        "data/account_reconcile_model_template.xml",
        "data/account_chart_template_configure_data.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "post_init_hook": "_l10n_fr_post_init_hook",
    "license": "LGPL-3",
}
