import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-l10n-france",
    description="Meta package for oca-l10n-france Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-account_banking_fr_lcr>=15.0dev,<15.1dev',
        'odoo-addon-l10n_fr_account_tax_unece>=15.0dev,<15.1dev',
        'odoo-addon-l10n_fr_department>=15.0dev,<15.1dev',
        'odoo-addon-l10n_fr_department_oversea>=15.0dev,<15.1dev',
        'odoo-addon-l10n_fr_ecotaxe>=15.0dev,<15.1dev',
        'odoo-addon-l10n_fr_siret>=15.0dev,<15.1dev',
        'odoo-addon-l10n_fr_state>=15.0dev,<15.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 15.0',
    ]
)
