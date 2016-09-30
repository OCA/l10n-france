# -*- coding: utf-8 -*-
# © 2014-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Balance EBP CSV export',
    'version': '8.0.1.1.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'http://www.akretion.com',
    'depends': ['account_financial_report_webkit'],
    'data': [
        'wizard/trial_balance_wizard_view.xml'
    ],
    'installable': True,
    'external_dependencies': {'python': ['unicodecsv']},
}
