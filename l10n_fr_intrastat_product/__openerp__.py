# -*- encoding: utf-8 -*-
##############################################################################
#
#    France Intrastat Product module for Odoo
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
    'version': '1.2',
    'category': 'Localisation/Report Intrastat',
    'license': 'AGPL-3',
    'summary': "Add support for the Déclaration d'Échange de Biens (DEB) "
               "for France",
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'http://www.akretion.com',
    'depends': [
        'intrastat_product',
        'sale_stock',
        'purchase',
        'l10n_fr_siret',
        ],
    'data': [
        'security/intrastat_product_security.xml',
        'security/ir.model.access.csv',
        'intrastat_type_data.xml',
        'intrastat_product_view.xml',
        'intrastat_type_view.xml',
        'intrastat_product_reminder.xml',
        'company_view.xml',
        'partner_view.xml',
        'product_view.xml',
        'stock_view.xml',
        'invoice_view.xml',
    ],
    'demo': ['intrastat_demo.xml'],
    'installable': True,
    'application': True,
}
