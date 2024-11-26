# Copyright 2016-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "French Overseas Departments (DOM)",
    "summary": "Populate Database with overseas French "
    "Departments (Départements d'outre-mer)",
    "version": "18.0.1.0.0",
    "category": "French Localization",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "license": "AGPL-3",
    "depends": ["l10n_fr_department"],
    "data": [
        "data/res_country_state.xml",
        "data/res_country_department.xml",
    ],
    "pre_init_hook": "create_fr_oversea_state_xmlid",
    "post_init_hook": "set_oversea_department_on_partner",
    "installable": True,
}
