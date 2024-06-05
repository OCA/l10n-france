# © 2014-2023 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountEcotaxeClassification(models.Model):
    _name = "account.ecotaxe.classification"
    _description = "Account Ecotaxe Classification"

    @api.model
    def _default_company_id(self):
        return self.env.company

    name = fields.Char(required=True)
    code = fields.Char()
    ecotaxe_type = fields.Selection(
        [("fixed", "Fixed"), ("weight_based", "Weight based")],
        required=True,
        help="If ecotaxe is weight based,"
        "the ecotaxe coef must take into account\n"
        "the weight unit of measure (kg by default)",
    )
    ecotaxe_coef = fields.Float(
        digits="Ecotaxe", compute="_compute_ecotaxe_vals", readonly=False, store=True
    )
    default_fixed_ecotaxe = fields.Float(
        digits="Ecotaxe",
        help="Default fixed ecotaxe amount.",
        compute="_compute_ecotaxe_vals",
        readonly=False,
        store=True,
    )
    categ_id = fields.Many2one(
        comodel_name="account.ecotaxe.category",
        string="Category",
    )
    sector_id = fields.Many2one(
        comodel_name="ecotaxe.sector",
        string="Ecotaxe sector",
    )
    collector_id = fields.Many2one(
        comodel_name="ecotaxe.collector",
        string="Ecotaxe collector",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=_default_company_id,
        help="Specify a company"
        " if you want to define this Ecotaxe Classification only for specific"
        " company. Otherwise, this Fiscal Classification will be available"
        " for all companies.",
    )
    product_status = fields.Selection(
        [("M", "Menager"), ("P", "Professionnel")],
        required=True,
    )
    supplier_status = fields.Selection(
        [
            ("FAB", "Fabricant"),
            ("REV", "Revendeur sous sa marque"),
            ("INT", "Introducteur"),
            ("IMP", "Importateur"),
            ("DIS", "Vendeur à distance"),
        ],
        required=True,
        help="FAB ==> Fabricant : est établi en France et fabrique des EEE\n"
        "sous son propre nom ou sa propre marque, ou fait concevoir ou\n"
        " fabriquer des EEE et les commercialise sous\n"
        " son propre nom et sa propre marque\n"
        "REV ==> Revendeur sous sa marque : est établi en France et vend,\n"
        " sous son propre nom ou sa propre marque des EEE produits\n"
        " par d'autres fournisseurs"
        "INT ==> Introducteur : est établi en France et met sur le marché\n"
        "des EEE provenant d'un autre Etat membre"
        "IMP ==> Importateur : est établi en France et met sur marché\n"
        "des EEE provenant de pays hors Union Européenne"
        "DIS ==> Vendeur à distance : est établie dans un autre Etat\n"
        "membre ou dans un pays tiers et vend en France des EEE par\n"
        "communication à distance",
    )
    emebi_code = fields.Char()
    scale_code = fields.Char()

    @api.depends("ecotaxe_type")
    def _compute_ecotaxe_vals(self):
        for classif in self:
            if classif.ecotaxe_type == "weight_based":
                classif.default_fixed_ecotaxe = 0
            if classif.ecotaxe_type == "fixed":
                classif.ecotaxe_coef = 0
