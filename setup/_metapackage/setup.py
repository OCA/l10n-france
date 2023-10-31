import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-l10n-france",
    description="Meta package for oca-l10n-france Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-account_balance_ebp_csv_export>=16.0dev,<16.1dev',
        'odoo-addon-account_banking_fr_lcr>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_fr_cfonb>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_account_invoice_facturx>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_account_tax_unece>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_account_vat_return>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_account_vat_return_teledec>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_chorus_account>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_chorus_facturx>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_chorus_sale>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_cog>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_das2>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_department>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_department_oversea>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_fec_oca>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_hr_check_ssnid>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_intrastat_product>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_intrastat_service>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_mis_reports>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_oca>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_pos_caisse_ap_ip>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_siret>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_siret_lookup>=16.0dev,<16.1dev',
        'odoo-addon-l10n_fr_state>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
