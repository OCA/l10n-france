# © 2014-2023 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ecotaxe_line_product_ids = fields.One2many(
        "ecotaxe.line.product",
        "product_tmplt_id",
        string="Ecotaxe lines",
        copy=True,
    )
    ecotaxe_amount = fields.Float(
        digits="Ecotaxe",
        compute="_compute_ecotaxe",
        help="Ecotaxe Amount computed form Classification",
        store=True,
    )

    @api.depends(
        "ecotaxe_line_product_ids",
        "ecotaxe_line_product_ids.classification_id",
        "ecotaxe_line_product_ids.classification_id.ecotaxe_type",
        "ecotaxe_line_product_ids.classification_id.ecotaxe_coef",
        "ecotaxe_line_product_ids.force_amount",
        "weight",
    )
    def _compute_ecotaxe(self):
        for tmpl in self:
            amount_ecotaxe = 0.0
            for ecotaxeline_prod in tmpl.ecotaxe_line_product_ids:
                ecotax_cls = ecotaxeline_prod.classification_id
                ecotaxe_line = 0.0
                if ecotax_cls.ecotaxe_type == "weight_based":
                    ecotaxe_line = ecotax_cls.ecotaxe_coef * (tmpl.weight or 0.0)
                else:
                    ecotaxe_line = ecotax_cls.default_fixed_ecotaxe
                # force ecotaxe amount by line
                if ecotaxeline_prod.force_amount:
                    ecotaxe_line = ecotaxeline_prod.force_amount
                amount_ecotaxe += ecotaxe_line
            tmpl.ecotaxe_amount = amount_ecotaxe
