# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import os.path
from dateutil.relativedelta import relativedelta
import logging
logger = logging.getLogger(__name__)
try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
except ImportError:
    logger.debug('Cannot import cryptography')


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
    fr_chorus_pwd_expiry_date = fields.Date(
        string='Chorus API Password Expiry Date')
    fr_chorus_cert_expiry_date = fields.Date(
        string='Chorus API Certificate Expiry Date', readonly=True)
    fr_chorus_expiry_remind_user_ids = fields.Many2many(
        'res.users', 'fr_chorus_api_expiry_remind_user_rel',
        'company_id', 'user_id', string='Users Receiving the Expiry Reminder')

    def chorus_get_api_certificates(self, raise_if_ko=False):
        """Inherit this method if you want to configure your Chorus certificates
        elsewhere or have per-company Chorus certificates"""
        self.ensure_one()
        cert_filepath = tools.config.get('chorus_api_cert')
        key_filepath = tools.config.get('chorus_api_key')
        if not cert_filepath:
            if raise_if_ko:
                raise UserError(_(
                    "Missing key 'chorus_api_cert' in Odoo server "
                    "configuration file"))
            else:
                logger.warning(
                    "Missing key 'chorus_api_cert' in Odoo server "
                    "configuration file")
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
                    "configuration file"))
            else:
                logger.warning(
                    "Missing key 'chorus_api_key-%d' in Odoo server "
                    "configuration file")
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
        return (cert_filepath, key_filepath)

    def read_cert_expiry_date(self, cert_filepath, raise_if_ko=False):
        expiry_date_dt = False
        with open(cert_filepath, 'r') as f:
            pem_data = f.read()
            try:
                backend = default_backend()
                logger.debug("Backend for chorus cert analysis: %s", backend)
                cert = x509.load_pem_x509_certificate(pem_data, backend)
            except Exception as e:
                if raise_if_ko:
                    raise UserError(_(
                        "Unable to get the expiry date of the certificate "
                        "%s. Error message: %s.") % (cert_filepath, e))
                else:
                    logger.error(
                        "Unable to get the expiry date of the certificate "
                        "%s. Error message: %s", cert_filepath, e)
                    return False
            expiry_date_dt = cert.not_valid_after
            logger.info(
                'Expiry date of certif. %s is %s',
                cert_filepath, expiry_date_dt)
        return expiry_date_dt

    def update_cert_expiry_date(self, raise_if_ko=False):
        for company in self:
            expiry_date = False
            res = company.chorus_get_api_certificates(raise_if_ko=raise_if_ko)
            if res:
                cert_filepath = res[0]
                expiry_date = self.read_cert_expiry_date(
                    cert_filepath, raise_if_ko=raise_if_ko)
            company.fr_chorus_cert_expiry_date = expiry_date

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
        today = fields.Date.context_today(self)
        if (
                self.fr_chorus_cert_expiry_date and
                self.fr_chorus_cert_expiry_date < today):
            if raise_if_ko:
                raise UserError(_(
                    "The expiry date of the certificate for Chorus API "
                    "is %s. You should deploy a new certificate.")
                    % self.fr_chorus_cert_expiry_date)
            else:
                logger.warning(
                    "The Chorus Pro API certificate expired on %s",
                    self.fr_chorus_cert_expiry_date)
        if (
                self.fr_chorus_pwd_expiry_date and
                self.fr_chorus_pwd_expiry_date < today):
            if raise_if_ko:
                raise UserError(_(
                    "The expiry date of the technical user credentials for "
                    "Chorus API is %s. You should login to Chorus Pro, "
                    "generate new credentials for the technical user and "
                    "update it in the menu Accounting > Configuration > "
                    "Configuration.")
                    % self.fr_chorus_pwd_expiry_date)
            else:
                logger.warning(
                    "The Chorus Pro API credentials expired on %s",
                    self.fr_chorus_pwd_expiry_date)
        return api_params

    def chorus_expiry_remind_user_list(self):
        email_list = ','.join([
            user.email for user in self.fr_chorus_expiry_remind_user_ids
            if user.email])
        return email_list

    @api.model
    def chorus_api_expiry_reminder_cron(self):
        logger.info('Starting the Chorus Pro API expiry reminder cron')
        today_dt = fields.Date.from_string(fields.Date.context_today(self))
        limit_date = fields.Date.to_string(today_dt + relativedelta(days=15))
        companies = self.env['res.company'].search([
            ('fr_chorus_api_password', '!=', False),
            ('fr_chorus_api_login', '!=', False),
            ])
        companies.update_cert_expiry_date()
        mail_tpl = self.env.ref(
            'l10n_fr_chorus_account.chorus_api_expiry_reminder_mail_template')
        for company in companies:
            if (
                    (company.fr_chorus_cert_expiry_date and
                     company.fr_chorus_cert_expiry_date <= limit_date) or
                    (company.fr_chorus_pwd_expiry_date and
                     company.fr_chorus_pwd_expiry_date <= limit_date)):
                if company.fr_chorus_expiry_remind_user_ids:
                    days_ctx = {}
                    if company.fr_chorus_pwd_expiry_date:
                        days_ctx['pwd_days'] = (
                            fields.Date.from_string(
                                company.fr_chorus_pwd_expiry_date) -
                            today_dt).days
                    if company.fr_chorus_cert_expiry_date:
                        days_ctx['cert_days'] = (
                            fields.Date.from_string(
                                company.fr_chorus_cert_expiry_date) -
                            today_dt).days
                    mail_tpl.with_context(days_ctx).send_mail(company.id)
                    logger.info(
                        'The Chorus API expiry reminder has been sent '
                        'for company %s', company.name)
                else:
                    logger.warning(
                        'The Chorus API credentials or certificate will '
                        'soon expire for company %s but the field '
                        'fr_chorus_expiry_remind_user_ids is empty!',
                        company.name)
        logger.info('End of the Chorus Pro API expiry reminder cron')
