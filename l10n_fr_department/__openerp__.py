# -*- encoding: utf-8 -*-
################################################################################
#    See Copyright and Licence Informations undermentioned.
################################################################################
{
    'name': 'French Departments (Département)',
    'version': '0.1',
    'category': 'base',
    'description': """
Add French departments data
===========================

Feature:
--------
    * Create a new model res_country_department, sub division of the res_country_state;
    * Populate the table res_country_department with the french departments;

Technical informations:
-----------------------
    * Use 3166-2:FR codifications (more detail http://fr.wikipedia.org/wiki/ISO_3166-2:FR);

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
        'l10n_fr_state',
        ],
    'data': [
            'security/ir.model.access.csv',
            'data/res_country_department_data.yml',
            'view/view.xml',
            'view/action.xml',
            'view/menu.xml',
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
    'images': ['static/src/img/screenshots/1.png'],
}
