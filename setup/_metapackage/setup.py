import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo8-addons-oca-l10n-france",
    description="Meta package for oca-l10n-france Odoo addons",
    version=version,
    install_requires=[
        'odoo8-addon-account_balance_ebp_csv_export',
        'odoo8-addon-account_bank_statement_import_fr_cfonb',
        'odoo8-addon-account_banking_fr_lcr',
        'odoo8-addon-l10n_fr_account_tax_unece',
        'odoo8-addon-l10n_fr_base_location_geonames_import',
        'odoo8-addon-l10n_fr_business_document_import',
        'odoo8-addon-l10n_fr_chorus_account',
        'odoo8-addon-l10n_fr_chorus_sale',
        'odoo8-addon-l10n_fr_chorus_sale_stock',
        'odoo8-addon-l10n_fr_chorus_ubl',
        'odoo8-addon-l10n_fr_department',
        'odoo8-addon-l10n_fr_department_delivery',
        'odoo8-addon-l10n_fr_ecotaxe',
        'odoo8-addon-l10n_fr_fec',
        'odoo8-addon-l10n_fr_intrastat_product',
        'odoo8-addon-l10n_fr_intrastat_service',
        'odoo8-addon-l10n_fr_mis_reports',
        'odoo8-addon-l10n_fr_naf_ape',
        'odoo8-addon-l10n_fr_siret',
        'odoo8-addon-l10n_fr_state',
        'odoo8-addon-l10n_fr_tax_sale_ttc',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 8.0',
    ]
)
