# © 2011 Numérigraphe SARL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'French NAF partner categories and APE code',
    'version': '11.0.1.0.0',
    'author': 'Numérigraphe SARL,Odoo Community Association (OCA)',
    'category': 'French Localization',
    'depends': [
        'l10n_eu_nace'
    ],
    'data': [
        'data/res.partner.category.csv',
        'views/partner.xml',
    ],
    'license': 'AGPL-3',
    'auto_install': False,
    'installable': True,
}
