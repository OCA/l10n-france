# Copyright (C) 2012 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# @author Julien WESTE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Origin Information for Products (French Departments)",
    "version": "12.0.1.1.1",
    "category": "Sales",
    "author": "GRAP",
    "website": "https://github.com/grap/grap-odoo-business",
    "license": "AGPL-3",
    "depends": ["product_origin", "l10n_fr_department"],
    "data": [
        "views/view_product_product.xml",
        "views/view_product_template.xml",
    ],
    "demo": [
        "demo/product_product.xml",
    ],
    "images": [],
    "installable": True,
}
