# Copyright 2017-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'L10n FR Chorus UBL',
    'summary': "Generate Chorus-compliant UBL e-invoices",
    'version': '12.0.1.0.1',
    'category': 'French Localization',
    'author': "Akretion,Odoo Community Association (OCA)",
    'maintainers': ['alexis-via'],
    'development_status': 'Alpha',
    'website': 'https://github.com/OCA/l10n-france',
    'license': 'AGPL-3',
    'depends': [
        'l10n_fr_chorus_account',
        'account_invoice_ubl',
        ],
    'installable': True,
}
