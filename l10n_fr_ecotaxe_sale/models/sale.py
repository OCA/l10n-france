# © 2015 -2020 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

    subtotal_ecotaxe = fields.Float(
        store=True, compute="_compute_ecotaxe", oldname="amount_ecotaxe"
    )
    unit_ecotaxe_amount = fields.Float(
        string="ecotaxe Unit.",
        store=True,
        compute="_compute_ecotaxe",
    )

    @api.depends("product_id", "product_uom_qty")
    def _compute_ecotaxe(self):
        for line in self:
            line.unit_ecotaxe_amount = line.product_id.ecotaxe_amount

            if line.order_id.pricelist_id:
                cur = line.order_id.pricelist_id.currency_id
                line.unit_ecotaxe_amount = cur.round(line.unit_ecotaxe_amount)
            line.subtotal_ecotaxe = line.unit_ecotaxe_amount * line.product_uom_qty


class SaleOrder(models.Model):

    _inherit = "sale.order"

    amount_ecotaxe = fields.Float(
        string="Included Ecotaxe", store=True, compute="_compute_ecotaxe"
    )

    @api.depends("order_line.subtotal_ecotaxe")
    def _compute_ecotaxe(self):
        for order in self:
            val_ecotaxe = 0.0
            for line in order.order_line:
                val_ecotaxe += line.subtotal_ecotaxe
            order.amount_ecotaxe = val_ecotaxe
