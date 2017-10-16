# -*- coding: utf-8 -*-
# © 2015-2017 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>

{
    'name': 'MIS reports for France',
    'version': '10.0.1.0.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'MIS Report templates for the French P&L and Balance Sheets',
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'http://www.akretion.com',
    'depends': ['mis_builder', 'l10n_fr'],
    'data': [
        'data/mis_report_styles.xml',
        'data/mis_report_pl.xml',
        'data/mis_report_pl_simplified.xml',
        'data/mis_report_bs.xml',
        'data/mis_report_bs_simplified.xml',
        ],
    'installable': True,
}
