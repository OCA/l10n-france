# Copyright 2013-2019 Akretion France (http://www.akretion.com/)
# Copyright 2016-2019 Odoo SA (https://www.odoo.com/fr_FR/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>

{
    "name": "France - FEC",
    "category": "Accounting",
    "version": "12.0.1.0.0",
    "license": "LGPL-3",
    "summary": "Fichier d'Échange Informatisé (FEC) for France",
    "author": "Akretion,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["l10n_fr", "account", "date_range"],
    "external_dependencies": {
        "python": ["unicodecsv", "unidecode"],
        },
    "data": [
        "wizard/account_fr_fec_oca_view.xml",
    ],
    "installable": True,
}
