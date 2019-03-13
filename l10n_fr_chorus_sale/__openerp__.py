# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u'L10n FR Chorus Sale',
    'summary': "Set public market on sale orders",
    'version': '8.0.1.0.0',
    'category': 'French Localization',
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'license': 'AGPL-3',
    'depends': [
        'sale_commercial_partner',
        'l10n_fr_chorus_account',
        ],
    'data': [
        'views/sale_order.xml',
        'views/public_market.xml',
        ],
    'installable': True,
    'auto_install': True,
}
