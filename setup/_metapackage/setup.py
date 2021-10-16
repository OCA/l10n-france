import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo12-addons-oca-l10n-france",
    description="Meta package for oca-l10n-france Odoo addons",
    version=version,
    install_requires=[
        'odoo12-addon-account_balance_ebp_csv_export',
        'odoo12-addon-account_bank_statement_import_fr_cfonb',
        'odoo12-addon-account_banking_fr_lcr',
        'odoo12-addon-l10n_fr_account_invoice_facturx',
        'odoo12-addon-l10n_fr_account_tax_unece',
        'odoo12-addon-l10n_fr_business_document_import',
        'odoo12-addon-l10n_fr_chorus_account',
        'odoo12-addon-l10n_fr_chorus_facturx',
        'odoo12-addon-l10n_fr_chorus_sale',
        'odoo12-addon-l10n_fr_chorus_ubl',
        'odoo12-addon-l10n_fr_cog',
        'odoo12-addon-l10n_fr_das2',
        'odoo12-addon-l10n_fr_department',
        'odoo12-addon-l10n_fr_department_oversea',
        'odoo12-addon-l10n_fr_fec_oca',
        'odoo12-addon-l10n_fr_intrastat_product',
        'odoo12-addon-l10n_fr_intrastat_service',
        'odoo12-addon-l10n_fr_mis_reports',
        'odoo12-addon-l10n_fr_siret',
        'odoo12-addon-l10n_fr_state',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 12.0',
    ]
)
