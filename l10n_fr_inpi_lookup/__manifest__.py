{
    "name": "INPI Lookup",
    "summary": "Lookup partner via INPI API",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/l10n-france",
    "author": "Le Filament, Odoo Community Association (OCA)",
    "depends": ["l10n_fr_siret"],
    "external_dependencies": {
        "python": ["requests", "python-stdnum", "jwt", "pydantic"]
    },
    "data": [
        "wizard/fr_inpi_lookup_view.xml",
        "views/res_company.xml",
        "views/api_inpi_mapping.xml",
        "views/api_inpi_views.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
}
