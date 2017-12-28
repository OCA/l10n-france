# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, tools, _
from odoo.exceptions import UserError
import os.path
import logging
logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    fr_chorus_api_login = fields.Char(
        string='Chorus API Login',
        help="Login of the Technical User for Chorus API")
    fr_chorus_api_password = fields.Char(
        string='Chorus API Password',
        help="Password of the Technical User for Chorus API")
    fr_chorus_qualif = fields.Boolean(
        'Chorus Test Mode', help='Use the Chorus Pro qualification website')
    # The values of the selection field below should
    # start with either 'xml_' or 'pdf_'
    fr_chorus_invoice_format = fields.Selection(
        [], string='Chorus Invoice Format')

    def chorus_get_api_certificates(self, raise_if_ko=False):
        self.ensure_one()
        company_id = self.id
        cert_filepath = tools.config.get('chorus_api_cert-%d' % company_id)
        key_filepath = tools.config.get('chorus_api_key-%d' % company_id)
        if not cert_filepath:
            if raise_if_ko:
                raise UserError(_(
                    "Missing key 'chorus_api_cert-%d' in Odoo server "
                    "configuration file") % company_id)
            else:
                logger.warning(
                    "Missing key 'chorus_api_cert-%d' in Odoo server "
                    "configuration file", company_id)
                return False
        if not os.path.isfile(cert_filepath):
            if raise_if_ko:
                raise UserError(_(
                    "The Chorus certificate file '%s' doesn't exist")
                    % cert_filepath)
            else:
                logger.warning(
                    "The Chorus certificate file '%s' doesn't exist",
                    cert_filepath)
                return False
        if not key_filepath:
            if raise_if_ko:
                raise UserError(_(
                    "Missing key 'chorus_api_key-%d' in Odoo server "
                    "configuration file") % company_id)
            else:
                logger.warning(
                    "Missing key 'chorus_api_key-%d' in Odoo server "
                    "configuration file", company_id)
                return False
        if not os.path.isfile(key_filepath):
            if raise_if_ko:
                raise UserError(_(
                    "The Chorus key file '%s' doesn't exist")
                    % key_filepath)
            else:
                logger.warning(
                    "The Chorus key file '%s' doesn't exist",
                    key_filepath)
                return False
        # TODO check certificat validity here ?
        return (cert_filepath, key_filepath)

    def chorus_get_api_params(self, raise_if_ko=False):
        self.ensure_one()
        api_params = {}
        cert = self.chorus_get_api_certificates(raise_if_ko=raise_if_ko)
        if (
                self.fr_chorus_invoice_format and
                self.fr_chorus_api_login and
                self.fr_chorus_api_password and
                cert):
            api_params = {
                'login': self.fr_chorus_api_login.strip(),
                'password': self.fr_chorus_api_password.strip(),
                'qualif': self.fr_chorus_qualif,
                'cert': cert,
            }
        elif raise_if_ko:
            raise UserError(_(
                "Missing Chorus API parameters on the company %s")
                % self.display_name)
        else:
            logger.warning(
                'Some Chorus API parameters are missing on company %s',
                self.display_name)
        return api_params
