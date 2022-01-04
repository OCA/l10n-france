# Copyright 2021 Camptocamp
#   @author Silvio Gregorini <silvio.gregorini@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    ecotaxe_classification_id = fields.Many2one(
        "account.ecotaxe.classification",
        string="Ecotaxe Classification",
    )
    ecotaxe_amount = fields.Float(
        compute="_compute_ecotaxe",
        help="Ecotaxe Amount computed form Classification",
        store=True,
    )
    manual_fixed_ecotaxe = fields.Float(
        help="Manual Fixed ecotaxe.\n"
        "Allow to subtite default Ecotaxe Classification\n"
    )

    @api.model_create_multi
    def create(self, vals_list):
        prods = super().create(vals_list)
        prods._post_create_set_ecotax_classification()
        return prods

    def _post_create_set_ecotax_classification(self):
        for prod in self:
            tmpl = prod.product_tmpl_id
            # Case 1:
            #   * newly created product has an ecotax classification
            #   * the template has no classification
            #   * the product is the template's only variant
            # => copy ecotax from product to template
            if (
                prod.ecotaxe_classification_id
                and not tmpl.ecotaxe_classification_id
                and tmpl.product_variant_ids == prod
            ):
                tmpl.ecotaxe_classification_id = prod.ecotaxe_classification_id
            # Case 2:
            #   * newly created product has no ecotax classification
            #   * the template has ecotax classification
            # => copy ecotax from template to product
            elif not prod.ecotaxe_classification_id and tmpl.ecotaxe_classification_id:
                prod.ecotaxe_classification_id = tmpl.ecotaxe_classification_id

    @api.depends(
        "ecotaxe_classification_id",
        "ecotaxe_classification_id.ecotaxe_type",
        "ecotaxe_classification_id.ecotaxe_coef",
        "manual_fixed_ecotaxe",
        "weight",
        "product_tmpl_id.ecotaxe_amount",
    )
    def _compute_ecotaxe(self):
        for prod in self:
            ecotax_cls = prod.ecotaxe_classification_id
            if ecotax_cls.ecotaxe_type == "weight_based":
                amt = ecotax_cls.ecotaxe_coef * (prod.weight or 0.0)
            elif prod.manual_fixed_ecotaxe:
                amt = prod.manual_fixed_ecotaxe
            else:
                amt = ecotax_cls.default_fixed_ecotaxe
            prod.ecotaxe_amount = amt
