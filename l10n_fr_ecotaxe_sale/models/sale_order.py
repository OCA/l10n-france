# © 2015 -2023 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    amount_ecotaxe = fields.Float(
        digits="Ecotaxe",
        string="Included Ecotaxe",
        store=True,
        compute="_compute_ecotaxe",
    )

    @api.depends("order_line.subtotal_ecotaxe")
    def _compute_ecotaxe(self):
        for order in self:
            val_ecotaxe = 0.0
            for line in order.order_line:
                val_ecotaxe += line.subtotal_ecotaxe
            order.amount_ecotaxe = val_ecotaxe
