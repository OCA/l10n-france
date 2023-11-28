# Copyright 2010-2020 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "DES",
    "version": "16.0.1.4.0",
    "category": "Localisation/Report Intrastat",
    "license": "AGPL-3",
    "summary": "Module for Intrastat service reporting (DES) for France",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["intrastat_base", "report_xlsx_helper"],
    "external_dependencies": {"python": ["stdnum"]},
    "data": [
        "security/ir.model.access.csv",
        "views/intrastat_service_view.xml",
        "data/ir_cron.xml",
        "data/mail_template.xml",
        "security/intrastat_service_security.xml",
    ],
    "installable": True,
    "application": True,
}
