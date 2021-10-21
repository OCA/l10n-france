# -*- coding: utf-8 -*-
# © 2014-2021 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ecotaxe_classification_id = fields.Many2one(
        "account.ecotaxe.classification",
        string="Ecotaxe Classification",
        oldname="ecotaxe_classification_ids",
    )

class ProductProduct(models.Model):
    _inherit = "product.product"

    ecotaxe_amount = fields.Float(
        compute="_compute_ecotaxe",
        help="Ecotaxe Amount" "computed form Classification\n",
    )
    manual_fixed_ecotaxe = fields.Float(
        help="Manual Fixed ecotaxe.\n"
        "Allow to subtite default Ecotaxe Classification\n"
    )

    @api.model
    def _get_product_weight(self):
        """
        Overide this method to get the product wieight used to compute ecotaxe.
        net_weight or cross_weight
        Returns:
        """
        self.ensure_one()
        if 'weight_net' in self._fields:
            return self.weight_net
        else:
            return self.weight

    @api.depends(
        "ecotaxe_classification_id",
        "ecotaxe_classification_id.ecotaxe_type",
        "ecotaxe_classification_id.ecotaxe_coef",
        "weight",
        "manual_fixed_ecotaxe",
    )
    def _compute_ecotaxe(self):
        for prod in self:
            prod.ecotaxe_amount = 0.0
            ecotaxe_classif_id = prod.ecotaxe_classification_id
            if ecotaxe_classif_id.ecotaxe_type == "weight_based":
                weight = prod._get_product_weight() or 0.0
                prod.ecotaxe_amount = ecotaxe_classif_id.ecotaxe_coef * weight
            else:
                prod.ecotaxe_amount = (
                    prod.manual_fixed_ecotaxe
                    or ecotaxe_classif_id.default_fixed_ecotaxe
                )
