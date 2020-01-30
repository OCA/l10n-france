# -*- coding: utf-8 -*-
# © 2016-2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, SUPERUSER_ID
from odoo.tools import file_open
from lxml import etree
import logging
logger = logging.getLogger(__name__)


def setup_das2_accounts(cr, registry):
    f = file_open(
        'l10n_fr_das2/data/account_account_template.xml', 'rb')
    xml_root = etree.parse(f)
    data = {}
    for record in xml_root.xpath('//record'):
        xmlid = record.attrib['id']
        account_code = xmlid.split('_')[-1]
        for xfield in record.xpath('field'):
            data[account_code] = xfield.text
    logger.info('setup_das2_accounts data=%s', data)
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        companies = env['res.company'].search([])
        aao = env['account.account']
        for company in companies:
            logger.debug(
                'setup_das2_accounts working on company %s ID %d',
                company.display_name, company.id)
            if company.country_id and company.country_id != env.ref('base.fr'):
                continue
            for account_code, fr_das2 in data.items():
                accounts = aao.search([
                    ('company_id', '=', company.id),
                    ('code', '=ilike', account_code + '%')])
                accounts.write({'fr_das2': fr_das2})
                logger.info(
                    'Company %s: set fr_das2=%s on account IDs %s',
                    company.display_name, fr_das2, accounts.ids)
    return
