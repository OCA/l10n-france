# -*- coding: utf-8 -*-
# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'DAS2',
    'version': '10.0.1.0.0',
    'category': 'Accounting',
    'license': 'AGPL-3',
    'summary': 'DAS2 (France)',
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/l10n-france',
    'depends': ['account_fiscal_year', 'l10n_fr', 'l10n_fr_siret'],
    'data': [
        'security/das2_security.xml',
        'security/ir.model.access.csv',
        'data/account_account_template.xml',
        'views/l10n_fr_das2.xml',
        'views/account_account.xml',
        'views/account_config_settings.xml',
    ],
    'post_init_hook': 'setup_das2_accounts',
    'installable': True,
    'application': True,
}
