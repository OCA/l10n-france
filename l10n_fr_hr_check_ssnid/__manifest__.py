# Copyright 2018-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "French Localization - Check Social Security Number",
    "version": "16.0.1.0.0",
    "category": "Human Resources",
    "development_status": "Mature",
    "license": "AGPL-3",
    "summary": "Check validity of Social Security Numbers in French companies",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["hr"],
    "external_dependencies": {"python": ["stdnum"]},
    "data": ["views/hr_employee.xml"],
    "installable": True,
}
