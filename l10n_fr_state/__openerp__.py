# -*- encoding: utf-8 -*-
################################################################################
#    See Copyright and Licence Informations undermentioned.
################################################################################
{
    'name': 'French States (Région)',
    'version': '0.1',
    'category': 'base',
    'description': """
Add French states data
======================

Feature:
--------
    * Populate the table res_country_state with the french states. (named 'Région')

Technical information:
----------------------
    * Use 3166-2:FR codifications (more detail http://fr.wikipedia.org/wiki/ISO_3166-2:FR);
    * Only populate inner states; (no Guyane, Mayotte, etc...) because there are in the res_country table;
    * Change res_country_state.code size. (3 to 4);

Copyright, Authors and Licence:
-------------------------------
    * Copyright: 2013, Groupement Régional Alimentaire de Proximité;
    * Author: Sylvain LE GAL (https://twitter.com/legalsylvain);
    * Licence: AGPL-3 (http://www.gnu.org/licenses/);
    """,
    'author': 'GRAP',
    'website': 'http://www.grap.coop',
    'license': 'AGPL-3',
    'depends': [
        'base',
        ],
    'data': [
            'data/res_country_state_data.yml',
        ],
    'demo': [],
    'js': [],
    'css': [],
    'qweb': [],
    'images': [],
    'post_load': '',
    'application': False,
    'installable': True,
    'auto_install': False,
    'images': [
            'static/src/img/screenshots/1.png'
        ],
}
