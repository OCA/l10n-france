# © 2014-2020 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "France Custom Ecotaxe",
    "summary": "Use Ecotaxe in French localisation contexte",
    "version": "15.0.1.0.0",
    "author": "Akretion, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-france",
    "category": "Localization/Account Taxes",
    "license": "AGPL-3",
    "depends": ["account"],
    "data": [
        "data/decimal_precision.xml",
        "security/ir_rule.xml",
        "security/ir.model.access.csv",
        "views/account_ecotaxe_category_view.xml",
        "views/account_ecotaxe_classification_view.xml",
        "views/account_move_view.xml",
        "views/product_template_view.xml",
    ],
    "installable": True,
}
