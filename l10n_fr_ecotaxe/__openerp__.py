# -*- coding: utf-8 -*-
# © 2014-2016 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'France Custom Ecotaxe',
    'summary': 'Use Ecotaxe in French localisation contexte',
    'version': '8.0.0.1.0',
    'author': "Akretion,Odoo Community Association (OCA)",
    'website': 'http://www.akretion.com',
    'category': 'Localization/Account Taxes',
    'depends': [
        'account_accountant',
        'sale',
        'purchase'
    ],
    'data': [
        'data/account_data.xml',
        'security/ir_rule.xml',
        'security/ir_model_access.yml',
        'views/product_view.xml',
        'views/sale_view.xml',
        'views/purchase_view.xml',
        'views/account_view.xml',

    ],
    'application': False,
    'installable': True,
}
