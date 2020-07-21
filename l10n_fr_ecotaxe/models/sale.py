# -*- coding: utf-8 -*-
# © 2014-2016 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


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
