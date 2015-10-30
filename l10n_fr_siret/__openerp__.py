# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2011 Numérigraphe SARL.
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
    'name': 'French company identity numbers SIRET/SIREN/NIC',
    'version': '9.0.1.2.0',
    "category": 'French Localization',
    'author': u'Numérigraphe,Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'depends': ['l10n_fr', 'account'],
    # account is required only for the inherit of the partner form view
    # l10n_fr is required because we re-define the siret field on res.company
    'data': [
        'partner_view.xml',
        'company_view.xml',
    ],
    'demo': ['partner_demo.xml'],
    'installable': True,
}
