# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u'L10n FR Chorus',
    'summary': "Generate Chorus-compliant e-invoices",
    'version': '10.0.1.0.0',
    'category': 'French Localization',
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'license': 'AGPL-3',
    'depends': [
        'l10n_fr_siret',
        'account_invoice_transmit_method',
        'agreement_account',
        ],
    'data': [
        'data/transmit_method.xml',
        'views/partner.xml',
        ],
    'demo': ['demo/demo.xml'],
    'installable': True,
}
