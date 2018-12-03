# -*- coding: utf-8 -*-

# © 2017 Le Filament (<http://www.le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
	'name': 'SIREN Lookup',
	'summary': "Lookup partner company in French SIREN database",
	'version': '10.0.1.0',
	'license': 'AGPL-3',
	'author': 'LE FILAMENT',
	'category': 'Partner',
	'depends': ['base'],
	'contributors': [
                'Benjamin Rivier <benjamin-filament>',
		'Rémi Cazenave <remi-filament>',
        ],
	'website': 'http://www.le-filament.com',
	'data': [
		'wizard/wizard_siren.xml',
		'views/res_partner.xml',
	],
	'qweb': [
                'static/src/xml/*.xml',
        ],
}
