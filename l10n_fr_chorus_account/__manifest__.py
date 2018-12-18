# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u'L10n FR Chorus',
    'summary': "Generate Chorus-compliant e-invoices and transmit them "
               "via the Chorus API",
    'version': '10.0.2.1.0',
    'category': 'French Localization',
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'license': 'AGPL-3',
    'depends': [
        'l10n_fr_siret',
        'account_invoice_transmit_method',
        'agreement_account',
        ],
    'external_dependencies': {'python': ['cryptography']},
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',
        'data/transmit_method.xml',
        'data/cron.xml',
        'data/mail_template.xml',
        'wizard/account_invoice_chorus_send_view.xml',
        'views/chorus_flow.xml',
        'views/chorus_partner_service.xml',
        'views/partner.xml',
        'views/account_config_settings.xml',
        'views/account_invoice.xml',
        ],
    'demo': ['demo/demo.xml'],
    'installable': True,
}
