# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 Numérigraphe SARL.
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
    'name' : 'French NAF partner categories and APE code',
    'version' : '1.0',
    'author' : u'Numérigraphe SARL',
    'category': 'Accounting & Finance',
    'description' : '''This module imports the French official NAF \
nomenclature of partner activities as partner categories, as an extension to \
the NACE categories of the European Union. 

It will also add a field to the partner form, to enter the partner's APE \
(official main activity of the company), picked among the NAF nomenclature.

Note: The display of the APE on the partner form may be further improved by \
merging an unofficial branch into your OpenERP Server. This can be done with \
the following command in your server branch:
  bzr merge lp:~numerigraphe/openobject-server/6.0-partner-category-short-name
This module will operate correctly whether you patch the server or not.
''',
    'depends' : [
                 'base',
                 'l10n_eu_nace'
    ],
    'init_xml' : [],
    'demo_xml' : [],
    'update_xml' : [
        'data/res.partner.category.csv',
        'partner_view.xml',
    ],
    'active': False,
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
