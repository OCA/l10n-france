# © 2013-2016 GRAP (Sylvain LE GAL https://twitter.com/legalsylvain)
# © 2015-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'French Departments (Départements)',
    'summary': 'Populate Database with French Departments (Départements)',
    'version': '11.0.1.0.0',
    'category': 'French Localization',
    'author': 'GRAP, '
              'Akretion, '
              'Nicolas JEUDY, '
              'Odoo Community Association (OCA)',
    'website': 'http://www.grap.coop',
    'license': 'AGPL-3',
    'depends': [
        'l10n_fr_state',
        'contacts',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/res_country_department_data.yml',
        'view/res_country_department.xml',
        'view/res_partner.xml',
    ],
    'post_init_hook': 'set_department_on_partner',
    'images': [
        'static/src/img/screenshots/1.png'
    ],
    'installable': True,
}
