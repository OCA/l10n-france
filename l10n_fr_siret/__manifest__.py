# Copyright 2011-2022 Numérigraphe SARL.
# Copyright 2014-2022 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Improved SIRET/SIREN support",
    "summary": "Check validity of SIRET/SIREN on partners",
    "version": "19.0.1.0.0",
    "category": "French Localization",
    "author": "Numérigraphe,Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "license": "AGPL-3",
    "depends": ["l10n_fr", "mail"],
    "external_dependencies": {"python": ["python-stdnum"]},
    "data": ["views/res_partner.xml"],
    "demo": ["demo/partner_demo.xml"],
    "post_init_hook": "clean_bad_siren_siret",
    "installable": True,
    "development_status": "Mature",
}
