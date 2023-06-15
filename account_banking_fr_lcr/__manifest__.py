# Copyright 2014-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


{
    "name": "French Letter of Change",
    "summary": "Create French LCR CFONB files",
    "version": "15.0.2.0.0",
    "license": "AGPL-3",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "category": "French localisation",
    "depends": ["account_payment_order"],
    "external_dependencies": {"python": ["unidecode"]},
    "data": ["data/account_payment_method.xml"],
    "demo": ["demo/lcr_demo.xml"],
    "post_init_hook": "lcr_set_unece",
    "installable": True,
}
