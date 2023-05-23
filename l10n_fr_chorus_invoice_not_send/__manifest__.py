# Copyright 2023 Akretion France (http://www.akretion.com/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "L10n FR Chorus Invoice Forbidden Send",
    "summary": "Avoid to send Chorus to the administration via the Chorus API",
    "version": "14.0.1.0.0",
    "category": "French Localization",
    "author": "Akretion,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-france",
    "license": "AGPL-3",
    "depends": [
        "l10n_fr_chorus_account",
    ],
    "data": [
        "views/account_move.xml",
    ],
    "installable": True,
}
