# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'French Overseas Departments (DOM)',
    'summary': 'Populate Database with overseas French '
               "Departments (Départements d'outre-mer)",
    'version': '12.0.1.0.0',
    'category': 'French Localization',
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'http://www.akretion.com',
    'license': 'AGPL-3',
    'depends': ['l10n_fr_department'],
    'data': [
        'data/res_country_state.xml',
        'data/res_country_department.xml',
    ],
    'post_init_hook': 'set_oversea_department_on_partner',
    'images': [],
    'installable': True,
}
