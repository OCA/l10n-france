# -*- coding: utf-8 -*-
# © 2013-2017 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'France - FEC',
    'version': '8.0.0.2.0',
    'category': 'French Localization',
    'license': 'AGPL-3',
    'summary': "Fichier d'Échange Informatisé (FEC) for France",
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'depends': ['account_accountant'],
    'external_dependencies': {
        'python': ['unicodecsv', 'unidecode'],
        },
    'data': [
        'wizard/fec_view.xml',
    ],
    'installable': True,
}
