# Copyright 2023 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "International Credit Transfer for France",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "Regulatory reporting codes for ISO 20022 credit transfer files",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["l10n_fr", "account_payment_sepa_base"],
    "data": [
        "data/account_pain_regulatory_reporting.xml",
        "views/res_partner.xml",
    ],
    "installable": True,
    "auto_install": True,
}
