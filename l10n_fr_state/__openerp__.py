# -*- encoding: utf-8 -*-
##############################################################################
#
#    l10n FR States module for OpenERP
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
    'name': 'French States (Région)',
    'summary': 'Populate Database with French States (Région)',
    'version': '0.1',
    'category': 'base',
    'description': """
Populate Database with French States (Région)
=============================================

Feature:
--------
    * Populate the table res_country_state with the french states. """
    """(named 'Région')

Technical information:
----------------------
    * Use 3166-2:FR codifications without country prefix (more detail """
    """http://fr.wikipedia.org/wiki/ISO_3166-2:FR);
    * Only populate inner states; (no Guyane, Mayotte, etc...) because """
    """there are in the res_country table;

Copyright, Authors and Licence:
-------------------------------
    * Copyright: 2013-2014, GRAP, Groupement Régional Alimentaire de Proximité;
    * Author: Sylvain LE GAL (https://twitter.com/legalsylvain);
    * Licence: AGPL-3 (http://www.gnu.org/licenses/);""",
    'author': "GRAP,Odoo Community Association (OCA)",
    'website': 'http://www.grap.coop',
    'license': 'AGPL-3',
    'depends': [
        'base',
    ],
    'data': [
        'data/res_country_state_data.yml',
    ],
    'installable': True,
    'auto_install': False,
    'images': [
        'static/src/img/screenshots/1.png'
    ],
}
