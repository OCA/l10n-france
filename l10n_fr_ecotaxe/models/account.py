# -*- coding: utf-8 -*-
###############################################################################
#
#   Module for OpenERP
#   Copyright (C) 2015 Akretion (http://www.akretion.com).
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

__author__ = 'mourad.elhadj.mimoune'

from openerp import api, models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    is_ecotaxe = fields.Boolean('Ecotaxe',
                                help="Warning : To inculde Ecotaxe "
                                "in the VAT tax check this :\n"
                                "1: cochez  \"ncluded in base amount \"\n"
                                "2: The Ecotaxe sequence must be less then "
                                "VAT tax (in sale and purchase)")

    @api.onchange('is_ecotaxe')
    def onchange_is_ecotaxe(self):
        import pdb; pdb.set_trace()
        if self.is_ecotaxe:
            self.type = 'code'
            self.include_base_amount = True
            self.python_compute = """
# price_unit
# product: product.product object or None
# partner: res.partner object or None
result = product.fixed_ecotaxe or product.computed_ecotaxe or 0.0
            """
            self.python_compute_inv = self.python_compute
