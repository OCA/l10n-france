import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo10-addons-oca-l10n-france",
    description="Meta package for oca-l10n-france Odoo addons",
    version=version,
    install_requires=[
        'odoo10-addon-account_balance_ebp_csv_export',
        'odoo10-addon-account_bank_statement_import_fr_cfonb',
        'odoo10-addon-account_banking_fr_lcr',
        'odoo10-addon-hr_holidays_jours_ouvrables',
        'odoo10-addon-l10n_fr_account_invoice_factur-x',
        'odoo10-addon-l10n_fr_account_invoice_import_factur-x',
        'odoo10-addon-l10n_fr_account_tax_unece',
        'odoo10-addon-l10n_fr_base_location_geonames_import',
        'odoo10-addon-l10n_fr_business_document_import',
        'odoo10-addon-l10n_fr_chorus_account',
        'odoo10-addon-l10n_fr_chorus_factur-x',
        'odoo10-addon-l10n_fr_chorus_sale',
        'odoo10-addon-l10n_fr_chorus_ubl',
        'odoo10-addon-l10n_fr_cog',
        'odoo10-addon-l10n_fr_das2',
        'odoo10-addon-l10n_fr_department',
        'odoo10-addon-l10n_fr_department_delivery',
        'odoo10-addon-l10n_fr_department_oversea',
        'odoo10-addon-l10n_fr_fec_oca',
        'odoo10-addon-l10n_fr_hr_check_ssnid',
        'odoo10-addon-l10n_fr_intrastat_product',
        'odoo10-addon-l10n_fr_intrastat_service',
        'odoo10-addon-l10n_fr_mis_reports',
        'odoo10-addon-l10n_fr_naf_ape',
        'odoo10-addon-l10n_fr_siret',
        'odoo10-addon-l10n_fr_state',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 10.0',
    ]
)
