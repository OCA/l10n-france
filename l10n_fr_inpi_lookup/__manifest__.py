{
    "name": "INPI Lookup",
    "summary": "Lookup partner via INPI API",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/l10n-france",
    "author": "Le Filament, Odoo Community Association (OCA)",
    "depends": [
        "base_vat",
    ],
    "external_dependencies": {
        "python": ["requests", "python-stdnum", "jwt", "pydantic"]
    },
    "data": [
        "wizard/fr_inpi_lookup_view.xml",
        "views/res_company.xml",
        "views/res_config_settings_views.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
}
