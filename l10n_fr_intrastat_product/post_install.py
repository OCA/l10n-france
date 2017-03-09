# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, SUPERUSER_ID


def set_fr_company_intrastat(cr, registry):
    """This post_install script is required because, when the module
    is installed, Odoo creates the column in the DB and compute the field
    and THEN it loads the file data/res_country_department_data.yml...
    So, when it computes the field on module installation, the
    departments are not available in the DB, so the department_id field
    on res.partner stays null. This post_install script fixes this."""
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        fr_id = env.ref('base.fr').id
        fr_vat_tax_codes = [
            '20.0', '8.5', '10.0', '5.5', '2.1',
            '20.0-TTC', '8.5-TTC', '10.0-TTC', '5.5-TTC', '2.1-TTC',
            'ACH-20.0', 'ACH-8.5', 'ACH-10.0', 'ACH-5.5', 'ACH-2.1',
            'ACH-20.0-TTC', 'ACH-8.5-TTC', 'ACH-10.0-TTC', 'ACH-5.5-TTC',
            'ACH-2.1-TTC',
            'IMMO-20.0', 'IMMO-8.5', 'IMMO-10.0', 'IMMO-5.5', 'IMMO-2.1']
        companies = env['res.company'].search([
            ('partner_id.country_id', '=', fr_id)])
        out_inv_trans_id = env.ref(
            'l10n_fr_intrastat_product.intrastat_transaction_21_11').id
        out_ref_trans_id = env.ref(
            'l10n_fr_intrastat_product.intrastat_transaction_25').id
        in_inv_trans_id = env.ref(
            'l10n_fr_intrastat_product.intrastat_transaction_11_11').id
        for company in companies:
            company.write({
                'intrastat_transaction_out_invoice': out_inv_trans_id,
                'intrastat_transaction_out_refund': out_ref_trans_id,
                'intrastat_transaction_in_invoice': in_inv_trans_id,
                'intrastat_accessory_costs': True,
                })
            fr_vat_taxes = env['account.tax'].search([
                ('description', 'in', fr_vat_tax_codes)])
            fr_vat_taxes.write({'exclude_from_intrastat_if_present': True})
    return
