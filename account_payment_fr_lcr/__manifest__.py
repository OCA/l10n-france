# Copyright 2014-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


{
    "name": "French Letter of Change",
    "summary": "Create French LCR CFONB files",
    "version": "18.0.1.1.0",
    "license": "AGPL-3",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "category": "French localisation",
    "depends": ["account_payment_batch_oca"],
    "external_dependencies": {"python": ["unidecode", "pypdf>=3.1.0"]},
    "data": [
        "data/account_payment_method.xml",
        "views/account_payment_method_line.xml",
        "views/account_payment_order.xml",
        "views/account_move.xml",
    ],
    "post_init_hook": "lcr_set_unece",
    "installable": True,
}
