import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo12-addons-oca-l10n-france",
    description="Meta package for oca-l10n-france Odoo addons",
    version=version,
    install_requires=[
        'odoo12-addon-l10n_fr_account_tax_unece',
        'odoo12-addon-l10n_fr_department',
        'odoo12-addon-l10n_fr_department_oversea',
        'odoo12-addon-l10n_fr_siret',
        'odoo12-addon-l10n_fr_state',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
