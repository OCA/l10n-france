# © 2014-2023 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class EcotaxeLineProduct(models.Model):
    """class for objects which can be used to save
    multi ecotaxe classification by product."""

    _name = "ecotaxe.line.product"
    _description = "Ecotaxe Line product"

    product_tmplt_id = fields.Many2one(
        "product.template", string="Product Template", readonly=True
    )
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    currency_id = fields.Many2one(related="product_tmplt_id.currency_id", readonly=True)
    classification_id = fields.Many2one(
        "account.ecotaxe.classification",
        string="Classification",
    )
    force_amount = fields.Float(
        digits="Ecotaxe",
        help="Force ecotaxe amount.\n"
        "Allow to substitute default Ecotaxe Classification\n",
    )
    amount = fields.Float(
        digits="Ecotaxe",
        compute="_compute_ecotaxe",
        help="Ecotaxe Amount computed form Classification or " "forced ecotaxe amount",
        store=True,
    )
    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("classification_id", "amount")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.classification_id.name} {rec.amount}"

    @api.depends(
        "classification_id",
        "classification_id.ecotaxe_type",
        "classification_id.ecotaxe_coef",
        "force_amount",
    )
    def _compute_ecotaxe(self):
        for ecotaxeline in self:
            ecotax_cls = ecotaxeline.classification_id

            if ecotax_cls.ecotaxe_type == "weight_based":
                amt = ecotax_cls.ecotaxe_coef * (
                    ecotaxeline.product_tmplt_id.weight
                    or ecotaxeline.product_id.weight
                    or 0.0
                )
            else:
                amt = ecotax_cls.default_fixed_ecotaxe
            # force ecotaxe amount
            if ecotaxeline.force_amount:
                amt = ecotaxeline.force_amount
            ecotaxeline.amount = amt

    _sql_constraints = [
        (
            "unique_classification_id_by_product",
            "UNIQUE(classification_id, product_id)",
            "Only one ecotaxe classification occurrence by product",
        ),
        (
            "unique_classification_id_by_product_tmpl",
            "UNIQUE(classification_id, product_tmplt_id)",
            "Only one ecotaxe classification occurrence by product Template",
        ),
    ]
