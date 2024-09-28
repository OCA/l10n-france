# Copyright 2010-2022 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "EMEBI",
    "version": "16.0.1.3.0",
    "category": "Localisation/Report Intrastat",
    "license": "AGPL-3",
    "summary": "EMEBI (ex-DEB) for France",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": [
        "l10n_fr",
        "intrastat_product",
        "l10n_fr_department",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/account_fiscal_position_template.xml",
        "data/intrastat_fr_regime.xml",
        "views/intrastat_product_declaration.xml",
        "views/intrastat_fr_regime.xml",
        "views/intrastat_unit.xml",
        "data/intrastat_product_reminder.xml",
        "views/res_config_settings.xml",
        "views/product_template.xml",
    ],
    "post_init_hook": "set_fr_company_intrastat",
    "demo": ["demo/intrastat_demo.xml"],
    "installable": True,
    "application": True,
}
