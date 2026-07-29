# Copyright (C) 2016 Akretion (http://www.akretion.com/)

{
    "name": "Rapport RUP",
    "version": "18.0.1.0.0",
    "category": "French Localization",
    "summary": """ French fields and report for Registre Unique du Personnel """,
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["hr_contract", "l10n_fr_hr_check_ssnid"],
    "data": [
        "data/report_paperformat.xml",
        "report/report_rup.xml",
        "report/actions.xml",
        "views/hr_contract.xml",
        "views/hr_employee.xml",
        "views/hr_employee_pcs.xml",
        "security/ir.model.access.csv",
    ],
    "demo": ["demo/demo.xml"],
    "auto_install": False,
    "installable": True,
    "author": "Akretion, Odoo Community Association (OCA)",
    "license": "AGPL-3",
}
