# Copyright 2020-2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "DAS2",
    "version": "17.0.3.0.0",
    "category": "Invoicing Management",
    "license": "AGPL-3",
    "summary": "DAS2 (France)",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": [
        "l10n_fr_siret",
        "l10n_fr_cog",
    ],
    "external_dependencies": {
        "python": ["stdnum", "pyfrdas2>=0.10"],
    },
    "data": [
        "security/das2_security.xml",
        "security/ir.model.access.csv",
        "views/l10n_fr_das2.xml",
        "views/res_partner.xml",
    ],
    "demo": ["demo/demo.xml"],
    "installable": True,
}
