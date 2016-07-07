# -*- coding: utf-8 -*-
# © 2013-2016 GRAP (Sylvain LE GAL https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'French States (Région)',
    'summary': 'Populate Database with French States (Région)',
    'version': '9.0.0.1.1',
    'category': 'French Localization',
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
    'author': "GRAP,Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.grap.coop',
    'license': 'AGPL-3',
    'depends': ['base'],
    'data': ['data/res_country_state_data.yml'],
    'images': ['static/src/img/screenshots/1.png'],
    'installable': True,
}
