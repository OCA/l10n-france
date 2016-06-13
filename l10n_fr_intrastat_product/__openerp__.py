# -*- coding: utf-8 -*-
##############################################################################
#
#    L10n FR intrastat product module for Odoo
#    Copyright (C) 2010-2015 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'France Intrastat Product',
    'version': '8.0.2.0.0',
    'category': 'Localisation/Report Intrastat',
    'license': 'AGPL-3',
    'summary': 'Module for Intrastat product reporting (DEB) for France',
    'author': 'Akretion',
    'website': 'http://www.akretion.com',
    'depends': [
        'intrastat_product',
        'l10n_fr_siret',
        'l10n_fr_department',
        ],
    'data': [
        'security/intrastat_product_security.xml',
        'security/ir.model.access.csv',
        'intrastat_product_view.xml',
        'intrastat_transaction_data.xml',
        'intrastat_transaction_view.xml',
        'intrastat_product_reminder.xml',
        'company_view.xml',
        'partner_view.xml',
        'product_view.xml',
        'tax_view.xml',
        # 'stock_view.xml',
        # 'invoice_view.xml',
    ],
    'demo': ['intrastat_demo.xml'],
    'installable': True,
    'application': True,
}
