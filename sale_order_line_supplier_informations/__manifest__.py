# Copyright 2024 Moka
# @author Horvat Damien <damien@moka.cloud>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Sale Order Line Supplier Informations",
    "summary": "Add vendor informations to sale order line like cost and vendor reference",
    "version": "16.0.1.0.0",
    "author": "Moka",
    "website": "https://moka.cloud",
    "license": "AGPL-3",
    "category": "Moka Welcome",
    "depends": ["sale", "sale_margin"],
    "data": [
        "views/sale_order.xml",
    ],
    "auto-install": True,
}
