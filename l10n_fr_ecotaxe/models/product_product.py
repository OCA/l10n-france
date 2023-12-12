# Copyright 2021 Camptocamp
#   @author Silvio Gregorini <silvio.gregorini@camptocamp.com>
# Copyright 2023 Akretion (http://www.akretion.com)
# #   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.osv import expression


class ProductProduct(models.Model):
    _inherit = "product.product"

    additional_ecotaxe_line_product_ids = fields.One2many(
        "ecotaxe.line.product",
        "product_id",
        string="Additional ecotaxe lines",
        copy=True,
        domain="[('id', 'not in', ecotaxe_line_product_ids)]",
    )
    all_ecotaxe_line_product_ids = fields.One2many(
        "ecotaxe.line.product",
        compute="_compute_all_ecotaxe_line_product_ids",
        search="_search_all_ecotaxe_line_product_ids",
        string="Additional ecotaxe lines",
    )
    ecotaxe_amount = fields.Monetary(
        compute="_compute_product_ecotaxe",
        help="Ecotaxe Amount computed form all ecotaxe line classification",
        store=True,
    )

    @api.depends("ecotaxe_line_product_ids", "additional_ecotaxe_line_product_ids")
    def _compute_all_ecotaxe_line_product_ids(self):
        for product in self:
            product.all_ecotaxe_line_product_ids = (
                product.ecotaxe_line_product_ids
                | product.additional_ecotaxe_line_product_ids
            )

    def _search_all_ecotaxe_line_product_ids(self, operator, operand):
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            return [
                ("ecotaxe_line_product_ids", operator, operand),
                ("additional_ecotaxe_line_product_ids", operator, operand),
            ]
        return [
            "|",
            ("ecotaxe_line_product_ids", operator, operand),
            ("additional_ecotaxe_line_product_ids", operator, operand),
        ]

    @api.depends(
        "all_ecotaxe_line_product_ids",
        "all_ecotaxe_line_product_ids.ecotaxe_classification_id",
        "all_ecotaxe_line_product_ids.ecotaxe_classification_id.ecotaxe_type",
        "all_ecotaxe_line_product_ids.ecotaxe_classification_id.ecotaxe_coef",
        "all_ecotaxe_line_product_ids.force_ecotaxe_amount",
        "weight",
    )
    def _compute_product_ecotaxe(self):
        for product in self:
            amount_ecotaxe = 0.0
            for ecotaxeline_prod in product.all_ecotaxe_line_product_ids:
                ecotax_cls = ecotaxeline_prod.ecotaxe_classification_id
                ecotaxe_line = 0.0
                if ecotax_cls.ecotaxe_type == "weight_based":
                    ecotaxe_line = ecotax_cls.ecotaxe_coef * (product.weight or 0.0)
                else:
                    ecotaxe_line = ecotax_cls.default_fixed_ecotaxe
                # force ecotaxe amount by line
                if ecotaxeline_prod.force_ecotaxe_amount:
                    ecotaxe_line = ecotaxeline_prod.force_ecotaxe_amount
                amount_ecotaxe += ecotaxe_line
            product.ecotaxe_amount = amount_ecotaxe
