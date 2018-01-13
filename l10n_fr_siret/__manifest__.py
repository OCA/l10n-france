# © 2011 Numérigraphe SARL.
# © 2014-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'French company identity numbers SIRET/SIREN/NIC',
    'version': '11.0.1.0.0',
    "category": 'French Localization',
    'author': u'Numérigraphe,Akretion,Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'depends': ['l10n_fr', 'account'],
    # account is required only for the inherit of the partner form view
    # l10n_fr is required because we re-define the siret field on res.company
    'data': [
        'views/partner.xml',
        'views/company.xml',
    ],
    'demo': ['demo/partner_demo.xml'],
    'installable': True,
}
