# Copyright 2013-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2016-2020 Odoo SA (https://www.odoo.com/fr_FR/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>

{
    "name": "France - FEC",
    "category": "Accounting",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "summary": "Fichier d'Échange Informatisé (FEC) for France",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["l10n_fr", "account", "date_range"],
    "external_dependencies": {
        "python": ["unicodecsv", "unidecode"],
    },
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_fr_fec_oca_view.xml",
    ],
    "installable": True,
}
