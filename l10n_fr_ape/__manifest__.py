# @author: MonsieurB <monsieurb@saaslys.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'French APE Code',
    'summary': 'Add french company ape code links with partner company',
    'version': '12.0.1.0.0',
    'category': 'French Localization',
    'author': 'SAASLYS, '
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/l10n-france',
    'license': 'AGPL-3',
    'depends': ['base'],
    'data': [
        'views/res_partner_industry_view.xml',
        'data/res_partner_industry.xml'
    ],
    'installable': True,
}
