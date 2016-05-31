# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008 JAILLET Simon - CrysaLEAD - www.crysalead.fr
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301  USA
#
##############################################################################
{
    'name': 'France Custom Ecotaxe',
    'version': '1.1',
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'category': 'Localization/Account Taxes',
    'description': """
This is the module to manage the Ecotaxe for France in Odoo.
========================================================================

This module applies to companies based in France mainland. It doesn't apply to
companies based in the DOM-TOMs (Guadeloupe, Martinique, Guyane, Réunion,
Mayotte).

This localisation module add a field "is Ecotaxe" on Tax object.
It add Ecotaxe amount on sale line, purchase line and invoice line.
The fileds Untaxed amount include Ecotaxe amount for readability.
In fact Ecotaxe amount are included in base of VAT.

To make easy ecotaxe management, ecotaxe are set on products.
So product contain ecotaxe values (fixed or weight based).
On the taxe "Ecotaxe" we use python code to get a right ecotaxe
value from product.
One ecotaxe can be used for all products.
We recommend to use at least two ecotaxes :
1 for sale
2 for purchase

Adding ecotaxe on product category aims to facilitate ecotaxe setting.

""",
    'depends': [
        'account',
        'product',
        'sale',
        'purchase'
    ],
    'data': [
        'security/ir_rule.xml',
        'security/ir_model_access.yml',
        'views/product_view.xml',
        'views/sale_view.xml',
        'views/purchase_view.xml',
        'views/account_view.xml',

    ],
    'test': [],
    'demo': [],
    'auto_install': False,
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
