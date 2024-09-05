{
    "name": "payment paybox acquirer",
    "license": "AGPL-3",
    "summary": "Accept payments with Paybox secure payment gateway.",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "author": "Akretion, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-france",
    "external_dependencies": {"python": ["rsa"]},
    "depends": [
        "payment",
    ],
    "application": True,
    "installable": True,
    "data": [
        "views/payment_paybox_view.xml",
        "views/payment_paybox_template.xml",
        "data/payment_acquirer_data.xml",
    ],
}
