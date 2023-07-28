# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "POS: Caisse-AP payment protocol for France",
    "version": "16.0.1.0.0",
    "category": "Point of Sale",
    "license": "AGPL-3",
    "summary": "Add support for Caisse-AP payment protocol used in France",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["point_of_sale"],
    "data": [
        "views/pos_payment_method.xml",
    ],
    "assets": {
        "point_of_sale.assets": [
            "l10n_fr_pos_caisse_ap_ip/static/src/js/models.js",
            "l10n_fr_pos_caisse_ap_ip/static/src/js/payment_caisse_ap_ip.js",
        ],
    },
    "installable": True,
}
