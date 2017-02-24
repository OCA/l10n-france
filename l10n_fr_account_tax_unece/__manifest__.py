# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': u'L10n FR Account Tax UNECE',
    'summary': "Auto-configure UNECE params on French taxes",
    'version': '10.0.1.0.0',
    'category': 'French Localization',
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'license': 'AGPL-3',
    'depends': ['l10n_fr', 'account_tax_unece'],
    'post_init_hook': 'set_unece_on_taxes',
    'installable': True,
    'auto_installable': True,
}
