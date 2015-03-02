# -*- encoding: utf-8 -*-
##############################################################################
#
#    l10n FR Base Location Geonames Import module for OpenERP
#    Copyright (C) 2014 Akretion (http://www.akretion.com)
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
    'name': 'French Localization for Base Location Geonames Import',
    'version': '0.1',
    'category': 'Extra Tools',
    'license': 'AGPL-3',
    'summary': 'France-specific tuning for import of better zip entries '
    'from Geonames',
    'description': """
French Localization Base Location Geonames Import
=================================================

This module adds some France-specific tuning for the
wizard that imports better zip entries from Geonames
(http://download.geonames.org/export/zip/). This wizard is provided
by the module base_location_geonames_import from the projet
*partner-contact-management*. This tuning aims at complying with
France's postal standards published by *La Poste*. This tuning will
be applied for France and France-related territories where *La Poste*
postal standards apply.

This module has been written by Alexis de Lattre from Akretion
<alexis.delattre@akretion.com>.
    """,
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'depends': ['base_location_geonames_import'],
    'external_dependencies': {'python': ['unidecode']},
    'data': [],
    'installable': True,
}
