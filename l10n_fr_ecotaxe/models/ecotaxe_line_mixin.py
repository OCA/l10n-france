# © 2014-2023 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class EcotaxeLineMixin(models.AbstractModel):
    """Mixin class for objects which can be used to save
     multi ecotaxe calssification  by account move line
    or sale order line."""

    _name = "ecotaxe.line.mixin"
    _description = "Ecotaxe Line Mixin"

    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency")
    ecotaxe_classification_id = fields.Many2one(
        "account.ecotaxe.classification",
        string="Ecotaxe Classification",
    )
    ecotaxe_amount_unit = fields.Monetary(
        compute="_compute_ecotaxe",
        help="Ecotaxe Amount computed form Classification or Manuel ecotaxe",
        store=True,
    )
    force_ecotaxe_unit = fields.Monetary(
        help="Force ecotaxe.\n" "Allow to subtite default Ecotaxe Classification\n"
    )
    ecotaxe_amount_total = fields.Monetary(
        compute="_compute_ecotaxe",
        help="Ecotaxe Amount total computed form Classification or forced ecotaxe amount",
        store=True,
    )
    quantity = fields.Float(digits="Product Unit of Measure", readonly=True)

    @api.depends(
        "ecotaxe_classification_id",
        "force_ecotaxe_unit",
        "product_id",
        "quantity",
    )
    def _compute_ecotaxe(self):
        for ecotaxeline in self:
            ecotax_cls = ecotaxeline.ecotaxe_classification_id

            if ecotax_cls.ecotaxe_type == "weight_based":
                amt = ecotax_cls.ecotaxe_coef * (ecotaxeline.product_id.weight or 0.0)
            else:
                amt = ecotax_cls.default_fixed_ecotaxe
            # force ecotaxe amount
            if ecotaxeline.force_ecotaxe_unit:
                amt = ecotaxeline.force_ecotaxe_unit

            ecotaxeline.ecotaxe_amount_unit = amt
            ecotaxeline.ecotaxe_amount_total = (
                ecotaxeline.ecotaxe_amount_unit * ecotaxeline.quantity
            )
