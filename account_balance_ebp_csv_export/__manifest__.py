# -*- coding: utf-8 -*-
# © 2014-2018 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Balance EBP CSV export',
    'version': '10.0.1.0.0',
    'category': 'Accounting',
    'license': 'AGPL-3',
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'http://www.akretion.com',
    'depends': [
        'account_financial_report_qweb',
        'report_qweb_txt',
        ],
    'data': [
        'report.xml',
        'report/balance_ebp_csv.xml',
        'wizard/trial_balance_wizard_view.xml'
    ],
    'installable': True,
}
