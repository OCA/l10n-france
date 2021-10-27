# -*- coding: utf-8 -*-
# Copyright 2017-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u'L10n FR Chorus Factur-X',
    'summary': "Generate Chorus-compliant Factur-X invoices",
    'version': '10.0.1.0.0',
    'category': 'French Localization',
    'author': "Akretion,Odoo Community Association (OCA)",
    'maintainers': ['alexis-via'],
    'website': 'https://github.com/OCA/l10n-france',
    'license': 'AGPL-3',
    'depends': [
        'l10n_fr_chorus_account',
        'l10n_fr_account_invoice_factur-x',
        ],
    'installable': True,
    'auto_install': True,
}
