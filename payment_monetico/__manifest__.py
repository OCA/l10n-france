# Copyright 2024 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Payment Provider: Monetico",
    "summary": "Accept payments with Monetico secure payment gateway.",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "category": "Accounting/Payment Providers",
    "author": "Akretion,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["payment"],
    "data": [
        "views/payment_provider_views.xml",
        "views/payment_monetico_templates.xml",
        "data/payment_icon_data.xml",
        "data/payment_provider_data.xml",
    ],
    "application": False,
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
