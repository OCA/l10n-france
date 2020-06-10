# Copyright 2017-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'L10n FR Chorus',
    'summary': "Generate Chorus-compliant e-invoices and transmit them "
               "via the Chorus API",
    'version': '13.0.1.0.0',
    'category': 'French Localization',
    'author': "Akretion,Odoo Community Association (OCA)",
    'maintainers': ['alexis-via'],
    'website': 'https://github.com/OCA/l10n-france',
    'license': 'AGPL-3',
    'depends': [
        'l10n_fr_siret',
        'account_invoice_transmit_method',
        'agreement_account',
        'server_environment',
        ],
    'external_dependencies': {'python': ['requests_oauthlib']},
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
        'views/config_settings.xml',
        'views/account_move.xml',
        ],
    'demo': ['demo/demo.xml'],
    'installable': True,
}
