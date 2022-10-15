# Copyright 2015-2020 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "MIS reports for France",
    "version": "14.0.1.1.0",
    "category": "Accounting & Finance",
    "license": "AGPL-3",
    "summary": "MIS Report templates for the French P&L and Balance Sheets",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["mis_builder"],
    "data": [
        "data/mis_report_styles.xml",
        "data/mis_report_pl.xml",
        "data/mis_report_pl_simplified.xml",
        "data/mis_report_bs.xml",
        "data/mis_report_bs_simplified.xml",
    ],
    "installable": True,
}
