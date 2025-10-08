{
    "name": "France - FEC Custom",
    "version": "18.0.1.0.0",
    "category": "Localization",
    "summary": "Fichier d'Échange Informatisé (FEC) for France",
    "author": "Druidoo,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-france",
    "license": "AGPL-3",
    "depends": ["l10n_fr_fec_oca", "queue_job"],
    "data": [
        "data/mail_templates.xml",
        "wizard/account_fr_fec_view.xml",
    ],
    "installable": True,
    "auto_install": True,
}
