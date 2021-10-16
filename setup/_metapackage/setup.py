import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo13-addons-oca-l10n-france",
    description="Meta package for oca-l10n-france Odoo addons",
    version=version,
    install_requires=[
        'odoo13-addon-account_bank_statement_import_fr_cfonb',
        'odoo13-addon-account_banking_fr_lcr',
        'odoo13-addon-l10n_fr_account_tax_unece',
        'odoo13-addon-l10n_fr_department',
        'odoo13-addon-l10n_fr_department_oversea',
        'odoo13-addon-l10n_fr_intrastat_product',
        'odoo13-addon-l10n_fr_intrastat_service',
        'odoo13-addon-l10n_fr_siret',
        'odoo13-addon-l10n_fr_state',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 13.0',
    ]
)
