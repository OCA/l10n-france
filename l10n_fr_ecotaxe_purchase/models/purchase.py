# -*- coding: utf-8 -*-
# © 2015 -2021 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models


class PurchaseOrderLine(models.Model):

    _inherit = "purchase.order.line"

    subtotal_ecotaxe = fields.Float(
        store=True, compute="_compute_ecotaxe", oldname="amount_ecotaxe"
    )
    unit_ecotaxe_amount = fields.Float(
        string="ecotaxe Unit.",
        store=True,
        compute="_compute_ecotaxe",
    )

    @api.multi
    @api.depends("product_id", "product_qty")
    def _compute_ecotaxe(self):
        for line in self:
            line.unit_ecotaxe_amount = line.product_id.ecotaxe_amount

            if line.order_id:
                cur = line.order_id.currency_id
                line.unit_ecotaxe_amount = cur.round(line.unit_ecotaxe_amount)
            line.subtotal_ecotaxe = (
                line.unit_ecotaxe_amount * line.product_qty
            )

    @api.model
    def _calc_line_base_price(self, line):
        res = super(PurchaseOrderLine, self)._calc_line_base_price(line)
        return res + (line.unit_ecotaxe_amount or 0.0)

    @api.depends('unit_ecotaxe_amount')
    def _compute_amount(self):
        super(PurchaseOrderLine, self)._compute_amount()


class PurchaseOrder(models.Model):

    _inherit = "purchase.order"

    amount_ecotaxe = fields.Float(
        string="Included Ecotaxe", store=True, compute="_compute_ecotaxe"
    )

    @api.multi
    @api.depends("order_line.subtotal_ecotaxe")
    def _compute_ecotaxe(self):
        for order in self:
            val_ecotaxe = 0.0
            for line in order.order_line:
                val_ecotaxe += line.subtotal_ecotaxe
            order.amount_ecotaxe = val_ecotaxe

    @api.model
    def _prepare_inv_line(self, account_id, line):
        res = super(PurchaseOrder, self)._prepare_inv_line(account_id, line)
        res.update({
            'unit_ecotaxe_amount': line.unit_ecotaxe_amount,
        })
        return res

    @api.model
    def _prepare_order_line_move(
            self, order, order_line, picking_id, group_id):
        res = super(PurchaseOrder, self)._prepare_order_line_move(
            order, order_line, picking_id, group_id)
        for vals in res:
            vals['price_unit'] = (vals.get('price_unit', 0.0) +
                                  order_line.unit_ecotaxe_amount)
        return res
