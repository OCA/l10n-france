# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'French localization Acount reconcile post on validation',
    'summary': 'Leaves moves in unposted on reconcile only posts when validated.',
    'version': '12.0.1.0.0',
    'author': 'Camptocamp',
    'maintainer': 'Camptocamp',
    'category': 'Sale',
    'installable': True,
    'license': 'AGPL-3',
    'application': False,
    'depends': [
        'account',
        'l10n_fr_certification'
    ],
    'website': 'http://www.camptocamp.com',
    'data': [
        'views/account_views.xml'
    ],
}
