# -*- coding: utf-8 -*-
# © 2016-2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, SUPERUSER_ID

MAPPING = {
    '20.0': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    '20.0-TTC': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    '10.0': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    '10.0-TTC': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    '8.5': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    '8.5-TTC': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    '5.5': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    '5.5-TTC': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    '2.1': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    '2.1-TTC': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    'ACH-20.0': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    'ACH-20.0-TTC': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    'ACH-10.0': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    'ACH-10.0-TTC': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    'ACH-8.5': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    'ACH-8.5-TTC': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    'ACH-5.5': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    'ACH-5.5-TTC': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    'ACH-2.1': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    'ACH-2.1-TTC': {'categ': 'tax_categ_s', 'type': 'tax_type_vat'},
    'IMMO-20.0': {'categ': False, 'type': 'tax_type_vat'},
    'IMMO-10.0': {'categ': False, 'type': 'tax_type_vat'},
    'IMMO-8.5': {'categ': False, 'type': 'tax_type_vat'},
    'IMMO-5.5': {'categ': False, 'type': 'tax_type_vat'},
    'IMMO-2.1': {'categ': False, 'type': 'tax_type_vat'},
    'ACH_UE_due-20.0': {'categ': 'tax_categ_k', 'type': 'tax_type_vat'},
    'ACH_UE_due-10.0': {'categ': 'tax_categ_k', 'type': 'tax_type_vat'},
    'ACH_UE_due-8.5': {'categ': 'tax_categ_k', 'type': 'tax_type_vat'},
    'ACH_UE_due-5.5': {'categ': 'tax_categ_k', 'type': 'tax_type_vat'},
    'ACH_UE_due-2.1': {'categ': 'tax_categ_k', 'type': 'tax_type_vat'},
    'ACH_UE_ded.-20.0': {'categ': 'tax_categ_k', 'type': 'tax_type_vat'},
    'ACH_UE_ded.-10.0': {'categ': 'tax_categ_k', 'type': 'tax_type_vat'},
    'ACH_UE_ded.-8.5': {'categ': 'tax_categ_k', 'type': 'tax_type_vat'},
    'ACH_UE_ded.-5.5': {'categ': 'tax_categ_k', 'type': 'tax_type_vat'},
    'ACH_UE_ded.-2.1': {'categ': 'tax_categ_k', 'type': 'tax_type_vat'},
    'EXO-0': {'categ': 'tax_categ_e', 'type': 'tax_type_vat'},
    'EXPORT-0': {'categ': 'tax_categ_g', 'type': 'tax_type_vat'},
    'UE-0': {'categ': 'tax_categ_k', 'type': 'tax_type_vat'},
    'IMPORT-0': {'categ': 'tax_categ_g', 'type': 'tax_type_vat'},
    }


def set_unece_on_taxes(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        companies = env['res.company'].search([])
        for company in companies:
            if company.country_id and company.country_id != env.ref('base.fr'):
                continue
            taxes = env['account.tax'].search(
                [('company_id', '=', company.id)])
            for tax in taxes:
                if tax.description in MAPPING:
                    tdesc = tax.description
                    categ_id = MAPPING[tdesc]['categ'] and env.ref(
                        'account_tax_unece.' + MAPPING[tdesc]['categ']).id\
                        or False
                    utype_id = env.ref(
                        'account_tax_unece.' + MAPPING[tdesc]['type']).id
                    tax.write({
                        'unece_type_id': utype_id,
                        'unece_categ_id': categ_id,
                        })
    return
