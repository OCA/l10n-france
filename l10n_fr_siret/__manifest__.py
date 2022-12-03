# Copyright 2011-2021 Numérigraphe SARL.
# Copyright 2014-2021 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "French company identity numbers SIRET/SIREN/NIC",
    "version": "15.0.1.1.0",
    "category": "French Localization",
    "author": "Numérigraphe,Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "license": "AGPL-3",
    "depends": ["l10n_fr"],
    "external_dependencies": {"python": ["python-stdnum>=1.18"]},
    "data": [
        "views/res_partner.xml",
        "views/res_company.xml",
    ],
    "demo": ["demo/partner_demo.xml"],
    "post_init_hook": "set_siren_nic",
    "installable": True,
    "development_status": "Mature",
}
