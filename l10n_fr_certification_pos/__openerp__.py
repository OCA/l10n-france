# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "French Certification (Point of Sale)",
    "summary": "Certification for Point of Sale Module",
    "version": "8.0.1.0.0",
    "category": "Point Of sale",
    "website": "https://odoo-community.org/",
    "author": "GRAP, Akretion, Odoo Community Association (OCA), OpenERP SA",
    "license": "AGPL-3",
    "depends": [
        "point_of_sale",
        "l10n_fr_certification_abstract",
    ],
    "data": [
        "views/view_pos_order.xml",
        "views/view_pos_config.xml",
        "views/l10n_fr_certification_pos.xml",
    ],
    'qweb': [
        'static/src/xml/l10n_fr_certification_pos.xml',
    ],
    "demo": [
        "demo/stock_location.xml",
        "demo/account_journal.xml",
        "demo/account_fiscalyear.xml",
        "demo/account_account.xml",
        "demo/pos_config.xml",
        "demo/res_groups.xml",
    ],
    'post_init_hook': '_generate_pos_config_sequences',
    "installable": True,
}
