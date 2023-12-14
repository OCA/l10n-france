# Copyright (C) 2023 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "French PoS Certification - Update Draft order lines",
    "version": "16.0.1.0.1",
    "category": "Point of Sale",
    "summary": "fixes the French certification module implemented by Odoo,"
    " authorizing the modification of draft sales lines.",
    "depends": ["l10n_fr_pos_cert"],
    "website": "https://github.com/OCA/l10n-france",
    "author": "GRAP,Odoo Community Association (OCA)",
    "maintainers": ["legalsylvain"],
    "assets": {
        "point_of_sale.assets": [
            "l10n_fr_pos_cert_update_draft_order_line/static/src/js/models.js",
        ],
    },
    "license": "LGPL-3",
}
