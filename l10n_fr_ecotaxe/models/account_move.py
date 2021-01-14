# © 2021 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    subtotal_ecotaxe = fields.Float(
        store=True, compute="_compute_ecotaxe", oldname="amount_ecotaxe"
    )
    unit_ecotaxe_amount = fields.Float(
        string="ecotaxe Unit.",
        store=True,
        compute="_compute_ecotaxe",
    )

    @api.depends("product_id", "quantity")
    def _compute_ecotaxe(self):
        for line in self:
            line.unit_ecotaxe_amount = line.product_id.ecotaxe_amount

            if line.move_id:
                cur = line.move_id.currency_id
                line.unit_ecotaxe_amount = cur.round(line.unit_ecotaxe_amount)

            line.subtotal_ecotaxe = line.unit_ecotaxe_amount * line.quantity


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_ecotaxe = fields.Float(
        string="Included Ecotaxe", store=True, compute="_compute_ecotaxe"
    )

    @api.depends("invoice_line_ids.subtotal_ecotaxe")
    def _compute_ecotaxe(self):
        for move in self:
            val_ecotaxe = 0.0
            for line in move.invoice_line_ids:
                val_ecotaxe += line.subtotal_ecotaxe
            move.amount_ecotaxe = val_ecotaxe
