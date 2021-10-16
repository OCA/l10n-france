import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo9-addons-oca-l10n-france",
    description="Meta package for oca-l10n-france Odoo addons",
    version=version,
    install_requires=[
        'odoo9-addon-account_bank_statement_import_fr_cfonb',
        'odoo9-addon-account_banking_fr_lcr',
        'odoo9-addon-l10n_fr_base_location_geonames_import',
        'odoo9-addon-l10n_fr_department',
        'odoo9-addon-l10n_fr_department_oversea',
        'odoo9-addon-l10n_fr_naf_ape',
        'odoo9-addon-l10n_fr_siret',
        'odoo9-addon-l10n_fr_state',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 9.0',
    ]
)
