import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-l10n-france",
    description="Meta package for oca-l10n-france Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-account_balance_ebp_csv_export',
        'odoo14-addon-account_banking_fr_lcr',
        'odoo14-addon-account_statement_import_fr_cfonb',
        'odoo14-addon-l10n_fr_account_tax_unece',
        'odoo14-addon-l10n_fr_cog',
        'odoo14-addon-l10n_fr_das2',
        'odoo14-addon-l10n_fr_department',
        'odoo14-addon-l10n_fr_department_oversea',
        'odoo14-addon-l10n_fr_fec_oca',
        'odoo14-addon-l10n_fr_hr_check_ssnid',
        'odoo14-addon-l10n_fr_intrastat_service',
        'odoo14-addon-l10n_fr_mis_reports',
        'odoo14-addon-l10n_fr_siret',
        'odoo14-addon-l10n_fr_state',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
