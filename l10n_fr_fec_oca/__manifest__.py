# Copyright 2016-2025 Odoo SA (https://www.odoo.com/fr_FR/)
# Copyright 2013-2025 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>

{
    "name": "France - FEC",
    "category": "Accounting",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "summary": "Fichier d'Échange Informatisé (FEC) for France",
    "author": "Odoo S.A.,Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["l10n_fr_account", "date_range"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "wizards/account_fr_fec_oca_view.xml",
    ],
    "installable": True,
}
