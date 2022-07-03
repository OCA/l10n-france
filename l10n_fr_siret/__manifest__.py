# Copyright 2011 Numérigraphe SARL.
# Copyright 2014-2018 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'French company identity numbers SIRET/SIREN/NIC',
    'version': '12.0.1.0.2',
    "category": 'French Localization',
    'author': 'Numérigraphe,Akretion,Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'depends': ['l10n_fr'],
    'data': [
        'views/partner.xml',
        'views/company.xml',
    ],
    'demo': ['demo/partner_demo.xml'],
    'installable': True,
}
