# © 2014-2023 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "France sale Ecotaxe",
    "summary": "Sale Ecotaxe used in French localisation contexte",
    "version": "16.0.2.0.0",
    "author": "Akretion,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-france",
    "category": "Localization/Account Taxes",
    "license": "AGPL-3",
    "depends": ["l10n_fr_ecotaxe", "sale"],
    "data": [
        "views/sale_view.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
}
