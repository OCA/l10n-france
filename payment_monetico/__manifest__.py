# Copyright 2024 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Monetico Payment Acquirer",
    "summary": "Accept payments with Monetico secure payment gateway.",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "category": "Accounting",
    "author": "Akretion,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["payment"],
    "data": [
        "views/payment_views.xml",
        "views/payment_monetico_templates.xml",
        "data/payment_acquirer_data.xml",
    ],
    "images": ["static/description/icon.png"],
    "installable": True,
}
