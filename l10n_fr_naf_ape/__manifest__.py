# -*- coding: utf-8 -*-
# © 2011 Numérigraphe SARL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'French NAF partner categories and APE code',
    'version': '10.0.1.0.0',
    'author': u'Numérigraphe SARL,Odoo Community Association (OCA)',
    'category': 'French Localization',
    'depends': [
        'l10n_eu_nace'
    ],
    'data': [
        'data/res.partner.category.csv',
<<<<<<< HEAD
<<<<<<< HEAD
        'views/partner.xml',
=======
        'views/partner_view.xml',
>>>>>>> [MIG] l10n_fr_naf_ape: Migrated to 10.0
=======
        'views/partner.xml',
>>>>>>> resolve confilcts
    ],
    'license': 'AGPL-3',
    'auto_install': False,
    'installable': True,
}
