# Copyright (C) 2026 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Point Of Sale - SIREN and NIC Fields",
    "summary": "SIREN and NIC Fields on PoS Customer form screen",
    "version": "16.0.1.0.2",
    "category": "Point Of Sale",
    "author": "GRAP, Odoo Community Association (OCA)",
    "maintainers": ["legalsylvain"],
    "website": "https://github.com/OCA/l10n-france",
    "license": "AGPL-3",
    "depends": ["l10n_fr_siret", "point_of_sale", "pos_partner_is_company"],
    "data": [],
    "assets": {
        "point_of_sale.assets": [
            "l10n_fr_siret_pos/static/src/xml/*.xml",
            "l10n_fr_siret_pos/static/src/js/*.esm.js",
        ],
    },
    "installable": True,
    "auto_install": False,
}
