# Copyright 2017-2019 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, SUPERUSER_ID
from odoo.tools import file_open
from lxml import etree
import logging
logger = logging.getLogger(__name__)


def set_fr_company_intrastat(cr, registry):
    """This post_install script is required because, when the module
    is installed, Odoo creates the column in the DB and compute the field
    and THEN it loads the file data/res_country_department_data.yml...
    So, when it computes the field on module installation, the
    departments are not available in the DB, so the department_id field
    on res.partner stays null. This post_install script fixes this."""
    f = file_open(
        'l10n_fr_intrastat_product/data/account_tax_template.xml', 'rb')
    xml_root = etree.parse(f)
    data = {}
    for record in xml_root.xpath('//record'):
        xmlid = record.attrib['id']
        data[xmlid] = {}
        for xfield in record.xpath('field'):
            xfield_dict = xfield.attrib
            data[xmlid][xfield_dict['name']] = xfield_dict.get('ref')
    logger.debug('set_unece_on_taxes data=%s', data)
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        imdo = env['ir.model.data']
        ato = env['account.tax']
        fr_id = env.ref('base.fr').id
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
            taxes = ato.search([('company_id', '=', company.id)])
            for tax in taxes:
                xmlid_obj = imdo.search([
                    ('model', '=', 'account.tax'),
                    ('module', '=', 'l10n_fr'),
                    ('res_id', '=', tax.id)], limit=1)
                if (
                        xmlid_obj and xmlid_obj.name and
                        len(xmlid_obj.name.split('_')) > 1):
                    # Remove the 'companyID_' prefix from XMLID of tax
                    xmlid_ori_end = '_'.join(xmlid_obj.name.split('_')[1:])
                    xmlid_ori = 'l10n_fr.%s' % xmlid_ori_end
                    if data.get(xmlid_ori):
                        logger.debug(
                            'set_fr_company_intrastat writing '
                            'exclude_from_intrastat_if_present=True on '
                            'tax ID %d', tax.id)
                        tax.write({'exclude_from_intrastat_if_present': True})
    return
