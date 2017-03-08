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
        companies = env['res.company'].search([
            ('partner_id.country_id', '=', fr_id)])
        for company in companies:
            company.intrastat_transaction_out_invoice = env.ref(
                'l10n_fr_intrastat_product.intrastat_transaction_21_11').id
            company.intrastat_transaction_out_refund = env.ref(
                'l10n_fr_intrastat_product.intrastat_transaction_25').id
            company.intrastat_transaction_in_invoice = env.ref(
                'l10n_fr_intrastat_product.intrastat_transaction_11_11').id
            company.intrastat_accessory_costs = True
    return
