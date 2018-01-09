# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "France - VAT Anti-Fraud Certification"
            " (CGI 286 I-3 bis) - Offline Mode",
    "summary": "Handle PoS offline mode for French Certification",
    "version": "10.0.1.0.0",
    "category": "Point Of sale",
    "website": "https://odoo-community.org/",
    "author": "GRAP, Odoo Community Association (OCA), OpenERP SA",
    "license": "AGPL-3",
    "depends": [
        "l10n_fr_pos_cert",
    ],
    "images": [
        "static/description/bill_unprinted.png",
        "static/description/bill_warning.png",
        "static/description/bill_with_hash.png",
        "static/description/pos_config.png",
    ],
    "data": [
        "views/view_pos_config.xml",
        "views/templates.xml",
    ],
    'qweb': [
        'static/src/xml/l10n_fr_certification_pos_offline.xml',
    ],
    "installable": True,
}
