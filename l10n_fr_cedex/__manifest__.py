# © 2019 Le Filament (<https://le-filament.com>)

{
    'name': 'Add Cedex on Partner',
    'version': '12.0.1.0.0',
    'category': 'Extra Tools',
    'license': 'AGPL-3',
    'summary': 'Adds Cedex on Partner',
    'author': "Le Filament,Odoo Community Association (OCA)",
    'website': 'https://le-filament.com',
    'depends': ['base'],
    'installable': True,
    "data": [
        "views/res_company.xml",
        "views/res_partner.xml",
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
