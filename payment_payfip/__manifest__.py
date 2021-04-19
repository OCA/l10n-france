# Copyright 2021 Moka Tourisme
# @author: Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Payment PayFIP",
    "category": "Payment Acquirer",
    "summary": "Payment Acquirer: PayFIP Implementation",
    "version": "12.0.1.0.0",
    "author": "Moka Tourisme,"
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "maintainers": ["ivantodorovich"],
    "depends": ["payment"],
    "data": [
        "views/assets.xml",
        "views/templates.xml",
        "views/payment_acquirer.xml",
        "data/payment_icon.xml",
        "data/payment_acquirer.xml",
    ],
}
