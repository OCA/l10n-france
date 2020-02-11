# coding: utf-8
{
    'name': 'France - FEC Custom',
    'version': '9.0.1.0.0',
    'category': 'Localization',
    'summary': "Fichier d'Échange Informatisé (FEC) for France",
    'author': "Druidoo",
    'website': 'http://www.druidoo.io',
    'depends': [
        'l10n_fr_fec',
        'connector'
    ],
    'data': [
        'data/ir_cron.xml',
        'data/mail_templates.xml',
        'wizard/fec_view.xml',
    ],
    'installable': True,
    'auto_install': True,
}
