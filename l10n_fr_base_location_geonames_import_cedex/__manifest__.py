# © 2019 Le Filament (<https://le-filament.com>)

{
    'name': 'French Cedex Localization for Base Location Geonames Import',
    'version': '12.0.1.0.0',
    'category': 'Extra Tools',
    'license': 'AGPL-3',
    'summary': 'Move Cedex from zip to cedex field when importing from '
               'Geonames',
    'author': "Le Filament,Odoo Community Association (OCA)",
    'website': 'https://le-filament.com',
    'depends': ['l10n_fr_base_location_geonames_import', 'l10n_fr_cedex'],
    'external_dependencies': {'python': ['unidecode']},
    'installable': True,
    "data": [
        "views/res_city_zip.xml",
    ]
}
