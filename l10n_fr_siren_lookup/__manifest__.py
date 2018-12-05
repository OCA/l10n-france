# -*- coding: utf-8 -*-
# © 2018 Le Filament (<https://le-filament.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "SIREN Lookup",
    "summary": "Lookup partner company in French SIREN database",
    "version": "10.0.1.0.0",
    "category": "Partner",
    "website": "https://github.com/OCA/l10n-france",
    "author": "Le Filament, Odoo Community Association (OCA)",
    "maintainers": ["remi-filament"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "base",
    ],
    "data": [
        "wizard/siren_wizard.xml",
        "views/res_partner.xml",
    ],
}
