# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat service module for OpenERP
#    Copyright (C) 2010-2011 Akretion (http://www.akretion.com). All Rights Reserved
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
Please contact Alexis de Lattre from Akretion for any help or question.
    """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com',
    'depends': ['l10n_fr_intrastat_base'],
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'intrastat_service_view.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
