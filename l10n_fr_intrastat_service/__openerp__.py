# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat service module for OpenERP (DES)
#    Copyright (C) 2010-2013 Akretion (http://www.akretion.com)
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
    'name': 'France Intrastat Service',
    'version': '1.1',
    'category': 'Localisation/Report Intrastat',
    'license': 'AGPL-3',
    'summary': 'Module for Intrastat service reporting (DES) for France',
    'description': """This module adds support for the "Déclaration Européenne des Services" (DES).

The DES declaration has been introduced on January 1st 2010 in France. All French companies must send this declaration each month to France's Customs administration if they sell services to other EU companies.

More information about the DES is available on this official web page : http://www.douane.gouv.fr/page.asp?id=3846

Please contact Alexis de Lattre from Akretion <alexis.delattre@akretion.com> for any help or question about this module.
    """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com',
    'depends': ['intrastat_base'],
    'data': [
        'security/ir.model.access.csv',
        'intrastat_service_view.xml',
        'intrastat_service_reminder.xml',
        'security/intrastat_service_security.xml',
    ],
    'demo': [],
    'installable': True,
    'active': False,
    'application': True,
}
