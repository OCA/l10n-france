# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Factur-X Invoices Import for France',
    'version': '10.0.1.0.0',
    'category': 'Localisation',
    'license': 'AGPL-3',
    'summary': "France-specific module to import Factur-X invoices",
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'http://www.akretion.com',
    'depends': [
        'account_invoice_import_factur-x',
        'l10n_fr_business_document_import',
        ],
    'auto_install': True,
    'installable': True,
}
