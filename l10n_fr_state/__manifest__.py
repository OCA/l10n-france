# -*- coding: utf-8 -*-
# Copyright 2013-2018 GRAP (Sylvain LE GAL https://twitter.com/legalsylvain)
# Copyright 2015-2018 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'French States (Régions)',
    'summary': 'Populate Database with French States (Régions)',
    'version': '12.0.1.0.0',
    'category': 'French Localization',
    'author': 'GRAP, '
              'Akretion, '
              'Nicolas JEUDY, '
              'Odoo Community Association (OCA)',
    'website': 'http://www.grap.coop',
    'license': 'AGPL-3',
    'depends': ['base'],
    'pre_init_hook': 'create_fr_state_xmlid',
    'data': ['data/res_country_state.xml'],
    'images': ['static/src/img/screenshots/1.png'],
    'installable': True,
}
