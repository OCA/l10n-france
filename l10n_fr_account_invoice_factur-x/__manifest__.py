# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Factur-X Invoices for France',
    'version': '10.0.1.0.0',
    'category': 'Localisation',
    'license': 'AGPL-3',
    'summary': "France-specific module to generate Factur-X invoices",
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'http://www.akretion.com',
    'depends': [
        'account_invoice_factur-x',
        'l10n_fr_siret',
        ],
    'auto_install': True,
    'installable': True,
}
