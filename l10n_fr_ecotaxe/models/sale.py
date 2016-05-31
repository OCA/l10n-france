# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
#    Copyright (C) 2015-TODAY Akretion <http://www.akretion.com>.
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

from openerp import api, fields, models


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"
    amount_ecotaxe = fields.Float(string='Ecotaxe', store=True,
                                  compute='_compute_ecotaxe')

    @api.depends('tax_id', 'product_id', 'product_uom_qty')
    def _compute_ecotaxe(self):
        for line in self:
            price = line._calc_line_base_price(line)
            qty = line._calc_line_quantity(line)
            ecotaxe_id = [tax.id for tax in line.tax_id if tax.is_ecotaxe]
            ecotaxe_id = self.env['account.tax'].browse(ecotaxe_id)
            val = 0.0
            if ecotaxe_id:
                taxes = ecotaxe_id.compute_all(
                    price, qty, line.product_id,
                    line.order_id.partner_id)['taxes']
                for t in taxes:
                    val += t.get('amount', 0.0)

            line.amount_ecotaxe = val
            if line.order_id:
                cur = line.order_id.pricelist_id.currency_id
                line.amount_ecotaxe = cur.round(
                    line.amount_ecotaxe)


class SaleOrder(models.Model):

    _inherit = "sale.order"

    amount_untaxed_with_ecotaxe = fields.Float(
        'Untaxed Amount with Ecotaxe', store=True,
        compute='_compute_ecotaxe')
    amount_ecotaxe = fields.Float(
        string='Included Ecotaxe', store=True,
        compute='_compute_ecotaxe')
    amount_tax_without_ecotaxe = fields.Float(
        string='Other Taxes', store=True,
        compute='_compute_ecotaxe')

    @api.multi
    @api.depends('amount_untaxed', 'order_line.tax_id',
                 'order_line.product_id', 'order_line.product_uom_qty')
    def _compute_ecotaxe(self):
        for order in self:
            val_ecotaxe = 0.0
            for line in order.order_line:
                val_ecotaxe += line.amount_ecotaxe
            order.amount_ecotaxe = val_ecotaxe
            order.amount_untaxed_with_ecotaxe = order.amount_untaxed \
                + val_ecotaxe
            order.amount_tax_without_ecotaxe = order.amount_tax - val_ecotaxe
