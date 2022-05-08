# Copyright 2017-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'L10n FR Chorus Sale',
    'summary': "Set public market on sale orders",
    'version': '11.0.1.0.0',
    'category': 'French Localization',
    'author': "Akretion,Odoo Community Association (OCA)",
    'maintainers': ['alexis-via'],
    'website': 'https://github.com/OCA/l10n-france',
    'license': 'AGPL-3',
    'depends': [
        'l10n_fr_chorus_account',
        'sale',
        ],
    'data': [
        'views/sale_order.xml',
        ],
    'installable': True,
    'auto_install': False,
}
