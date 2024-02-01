# © 2015 -2023 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class SaleOrderLine(models.Model):

    _inherit = "sale.order.line"

    ecotaxe_line_ids = fields.One2many(
        "sale.order.line.ecotaxe",
        "sale_order_line_id",
        string="Ecotaxe lines",
        copy=True,
    )
    subtotal_ecotaxe = fields.Float(store=True, compute="_compute_ecotaxe")
    ecotaxe_amount_unit = fields.Float(
        string="ecotaxe Unit.",
        store=True,
        compute="_compute_ecotaxe",
    )

    @api.depends(
        "currency_id",
        "ecotaxe_line_ids",
        "ecotaxe_line_ids.amount_unit",
        "ecotaxe_line_ids.amount_total",
    )
    def _compute_ecotaxe(self):
        for line in self:
            unit = sum(line.ecotaxe_line_ids.mapped("amount_unit"))
            subtotal_ecotaxe = sum(line.ecotaxe_line_ids.mapped("amount_total"))

            if line.currency_id:
                unit = line.currency_id.round(unit)
                subtotal_ecotaxe = line.currency_id.round(subtotal_ecotaxe)
            line.update(
                {
                    "ecotaxe_amount_unit": unit,
                    "subtotal_ecotaxe": subtotal_ecotaxe,
                }
            )

    @api.onchange("product_id")
    def _onchange_product_ecotaxe_line(self):
        """Unlink and recreate ecotaxe_lines when modifying the product_id."""
        if self.product_id:
            self.ecotaxe_line_ids = [(5,)]  # Remove all ecotaxe classification
            ecotax_cls_vals = []
            for ecotaxeline_prod in self.product_id.all_ecotaxe_line_product_ids:
                classif_id = ecotaxeline_prod.classification_id.id
                forced_amount = ecotaxeline_prod.force_amount
                ecotax_cls_vals.append(
                    (
                        0,
                        0,
                        {
                            "classification_id": classif_id,
                            "force_amount_unit": forced_amount,
                        },
                    )
                )
            self.ecotaxe_line_ids = ecotax_cls_vals
        else:
            self.ecotaxe_line_ids = [(5,)]

    def edit_ecotaxe_lines(self):
        view = {
            "name": ("Ecotaxe classification"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "sale.order.line",
            "view_id": self.env.ref(
                "l10n_fr_ecotaxe_sale.view_sale_line_ecotaxe_form"
            ).id,
            "type": "ir.actions.act_window",
            "target": "new",
            "res_id": self.id,
        }
        return view

    def _prepare_invoice_line(self, **optional_values):
        """Create equivalente ecotaxe_line_ids for account move line
        from sale order line ecotaxe_line_ids .
        """
        res = super()._prepare_invoice_line(**optional_values)
        ecotax_cls_vals = []
        for ecotaxeline in self.ecotaxe_line_ids:
            ecotax_cls_vals.append(
                (
                    0,
                    0,
                    {
                        "classification_id": ecotaxeline.classification_id.id,
                        "force_amount_unit": ecotaxeline.force_amount_unit,
                    },
                )
            )
        res["ecotaxe_line_ids"] = ecotax_cls_vals
        return res
