# -*- encoding: utf-8 -*-
##############################################################################
#
#    l10n FR Departments module for OpenERP
#    Copyright (C) 2013-2014 GRAP (http://www.grap.coop)
#    @author Sylvain LE GAL (https://twitter.com/legalsylvain)
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
    'name': 'French Departments (Départements)',
    'summary': 'Populate Database with French Departments (Départements)',
    'version': '0.1',
    'category': 'base',
    'description': """
Populate Database with French Departments (Départements)
========================================================

Feature:
--------
    * Create a new model res_country_department, sub division of the """
    """res_country_state;
    * Populate the table res_country_department with the french departments;

Technical informations:
-----------------------
    * Use 3166-2:FR codifications (more detail"""
    """http://fr.wikipedia.org/wiki/ISO_3166-2:FR);

Copyright, Authors and Licence:
-------------------------------
    * Copyright: 2013-2014, Groupement Régional Alimentaire de Proximité
    * Copyright: 2014, Akretion (http://www.akretion.com/)
    * Author: Sylvain LE GAL (https://twitter.com/legalsylvain)
    * Author: Alexis de Lattre <alexis.delattre@akretion.com>
    * Licence: AGPL-3 (http://www.gnu.org/licenses/)""",
    'author': "GRAP,Odoo Community Association (OCA)",
    'website': 'http://www.grap.coop',
    'license': 'AGPL-3',
    'depends': [
        'l10n_fr_state',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/res_country_department_data.yml',
        'view/view.xml',
        'view/action.xml',
        'view/menu.xml',
    ],
    'images': [
        'static/src/img/screenshots/1.png'
    ],
    'test': ['test/department.yml'],
}
