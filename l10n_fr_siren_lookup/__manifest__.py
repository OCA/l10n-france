# -*- coding: utf-8 -*-
# © 2018 Le Filament (<https://le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'SIREN Lookup',
    'summary': "Lookup partner company in French SIREN database",
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Le Filament, Odoo Community Association (OCA)',
    'category': 'Partner',
    'depends': [
        'base'
    ],
    'maintainers': [
        'remi-filament',
    ],
    'website': 'http://www.le-filament.com',
    'data': [
        'wizard/siren_wizard.xml',
        'views/res_partner.xml',
    ],
}
