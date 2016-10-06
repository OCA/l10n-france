# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'French Localization for Base Location Geonames Import',
    'version': '9.0.1.0.0',
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
    'installable': False,
}
