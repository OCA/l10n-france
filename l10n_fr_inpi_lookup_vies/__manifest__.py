{
    "name": "INPI VIES Lookup",
    "summary": "Check VIES",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/l10n-france",
    "author": "Le Filament, Odoo Community Association (OCA)",
    "depends": ["base_vat", "l10n_fr_inpi_lookup"],
    "external_dependencies": {"python": ["requests", "python-stdnum"]},
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
}
