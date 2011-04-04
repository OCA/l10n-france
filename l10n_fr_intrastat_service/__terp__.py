# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat service module for OpenERP (DES)
#    Copyright (C) 2010-2011 Akretion (http://www.akretion.com). All Rights Reserved
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
    'name': 'Module for Intrastat service reporting (DES) for France',
    'version': '1.1',
    'category': 'Localisation/Report Intrastat',
    'license': 'AGPL-3',
    'description': """This module adds support for the "Déclaration Européenne des Services" (DES).

The DES declaration has been introduced on January 1st 2010 in France. All French companies must send this declaration each month to France's Customs administration if they sell services to other EU companies.

More information about the DES is available on this official web page : http://www.douane.gouv.fr/page.asp?id=3846

Please contact Alexis de Lattre from Akretion <alexis.delattre@akretion.com> for any help or question about this module.
    """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com',
    'depends': ['intrastat_base'],
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'intrastat_service_view.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
