import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo11-addons-oca-l10n-france",
    description="Meta package for oca-l10n-france Odoo addons",
    version=version,
    install_requires=[
        'odoo11-addon-l10n_fr_department',
        'odoo11-addon-l10n_fr_department_oversea',
        'odoo11-addon-l10n_fr_intrastat_product',
        'odoo11-addon-l10n_fr_siret',
        'odoo11-addon-l10n_fr_state',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 11.0',
    ]
)
