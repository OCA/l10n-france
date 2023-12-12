# © 2014-2023 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class EcotaxeLineProduct(models.Model):
    """class for objects which can be used to save mutili ecotaxe calssification  by product."""

    _name = "ecotaxe.line.product"
    _description = "Ecotaxe Line product"

    product_tmplt_id = fields.Many2one(
        "product.template", string="Product Template", readonly=True
    )
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    currency_id = fields.Many2one(related="product_tmplt_id.currency_id", readonly=True)
    ecotaxe_classification_id = fields.Many2one(
        "account.ecotaxe.classification",
        string="Ecotaxe Classification",
    )
    force_ecotaxe_amount = fields.Monetary(
        help="Force ecotaxe.\n" "Allow to substitute default Ecotaxe Classification\n"
    )
    ecotaxe_amount = fields.Monetary(
        compute="_compute_ecotaxe",
        help="Ecotaxe Amount total computed form Classification or forced ecotaxe amount",
        store=True,
    )

    @api.depends(
        "ecotaxe_classification_id",
        "ecotaxe_classification_id.ecotaxe_type",
        "ecotaxe_classification_id.ecotaxe_coef",
        "force_ecotaxe_amount",
    )
    def _compute_ecotaxe(self):
        for ecotaxeline in self:
            ecotax_cls = ecotaxeline.ecotaxe_classification_id

            if ecotax_cls.ecotaxe_type == "weight_based":
                amt = ecotax_cls.ecotaxe_coef * (
                    ecotaxeline.product_tmplt_id.weight
                    or ecotaxeline.product_id.weight
                    or 0.0
                )
            else:
                amt = ecotax_cls.default_fixed_ecotaxe
            # force ecotaxe amount
            if ecotaxeline.force_ecotaxe_amount:
                amt = ecotaxeline.force_ecotaxe_amount
            ecotaxeline.ecotaxe_amount = amt
