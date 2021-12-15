# © 2014-2016 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ecotaxe_classification_id = fields.Many2one(
        "account.ecotaxe.classification",
        string="Ecotaxe Classification",
    )
    ecotaxe_amount = fields.Monetary(
        compute="_compute_ecotaxe",
        help="Ecotaxe Amount computed form Classification",
        store=True,
    )
    manual_fixed_ecotaxe = fields.Monetary(
        help="Manual Fixed ecotaxe.\n"
        "Allow to subtite default Ecotaxe Classification\n"
    )

    @api.depends(
        "ecotaxe_classification_id",
        "ecotaxe_classification_id.ecotaxe_type",
        "ecotaxe_classification_id.ecotaxe_coef",
        "weight",
        "manual_fixed_ecotaxe",
    )
    def _compute_ecotaxe(self):
        for tmpl in self:
            ecotax_cls = tmpl.ecotaxe_classification_id
            if ecotax_cls.ecotaxe_type == "weight_based":
                amt = ecotax_cls.ecotaxe_coef * (tmpl.weight or 0.0)
            elif tmpl.manual_fixed_ecotaxe:
                amt = tmpl.manual_fixed_ecotaxe
            else:
                amt = ecotax_cls.default_fixed_ecotaxe
            tmpl.ecotaxe_amount = amt
