# © 2014-2016 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AcountMoveLine(models.Model):
    _inherit = "account.move.line"

    subtotal_ecotaxe = fields.Float(store=True, compute="_compute_ecotaxe")
    unit_ecotaxe_amount = fields.Float(
        string="Ecotaxe Unit.",
        store=True,
        compute="_compute_ecotaxe",
    )

    @api.depends("move_id.currency_id", "product_id", "quantity")
    def _compute_ecotaxe(self):
        for line in self:
            unit = line.product_id.ecotaxe_amount
            if line.move_id.currency_id:
                unit = line.move_id.currency_id.round(unit)
            line.update(
                {
                    "unit_ecotaxe_amount": unit,
                    "subtotal_ecotaxe": unit * line.quantity,
                }
            )
