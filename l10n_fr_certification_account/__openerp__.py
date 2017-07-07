# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "French Certification (Account)",
    "summary": "Certification for Account Module",
    "version": "8.0.1.0.0",
    "category": "Account",
    "website": "https://odoo-community.org/",
    "author": "GRAP, Akretion, Odoo Community Association (OCA), OpenERP SA",
    "license": "AGPL-3",
    "depends": [
        "account",
        "l10n_fr_certification_abstract",
    ],
    "data": [
        "views/view_account_move.xml",
        "views/view_res_company.xml",
    ],
    "demo": [
        "demo/res_groups.xml",
    ],
    'post_init_hook': '_generate_company_sequences',
    "installable": True,
}
