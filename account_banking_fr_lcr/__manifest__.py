# -*- coding: utf-8 -*-
# © 2014-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


{
    'name': 'French Letter of Change',
    'summary': 'Create French LCR CFONB files',
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'category': 'French localisation',
    'depends': ['account_payment_order', 'document'],
    'external_dependencies': {
        'python': ['unidecode'],
        },
    'data': ['data/account_payment_method.xml'],
    'demo': ['demo/lcr_demo.xml'],
    'post_init_hook': 'update_bank_journals',
    'installable': True,
}
