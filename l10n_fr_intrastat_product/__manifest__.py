# -*- coding: utf-8 -*-
# © 2010-2017 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'DEB',
    'version': '10.0.1.0.0',
    'category': 'Localisation/Report Intrastat',
    'license': 'AGPL-3',
    'summary': "DEB (Déclaration d'Échange de Biens) for France",
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'http://www.akretion.com',
    'depends': [
        'intrastat_product',
        'l10n_fr_siret',
        'l10n_fr_department',
        ],
    'data': [
        'security/intrastat_product_security.xml',
        'security/ir.model.access.csv',
        'views/intrastat_product.xml',
        'data/intrastat_transaction.xml',
        'views/intrastat_transaction.xml',
        'views/intrastat_unit.xml',
        'data/intrastat_product_reminder.xml',
        'views/account_config_settings.xml',
        'views/partner.xml',
        'views/product.xml',
    ],
    'post_init_hook': 'set_fr_company_intrastat',
    'demo': ['demo/intrastat_demo.xml'],
    'installable': True,
    'application': True,
}
