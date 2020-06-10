# Copyright 2017-2020 Akretion France (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import requests
import json
import base64
import logging
logger = logging.getLogger(__name__)

try:
    from requests_oauthlib import OAuth2Session
except ImportError:
    logger.debug('Cannot import requests-oauthlib')

API_URL = "https://api.aife.economie.gouv.fr"
QUALIF_API_URL = "https://sandbox-api.aife.economie.gouv.fr"
TOKEN_URL = 'https://oauth.aife.economie.gouv.fr/api/oauth/token'
QUALIF_TOKEN_URL = 'https://sandbox-oauth.aife.economie.gouv.fr/api/oauth/token'
MARGIN_TOKEN_EXPIRY_SECONDS = 240


class ResCompany(models.Model):
    _inherit = 'res.company'

    fr_chorus_api_login = fields.Char(
        string='Chorus Technical User Login')
    fr_chorus_api_password = fields.Char(
        string='Chorus Technical User Password')
    fr_chorus_qualif = fields.Boolean(
        'Chorus Test Mode', help='Use the Chorus Pro qualification website')
    # The values of the selection field below should
    # start with either 'xml_' or 'pdf_'
    fr_chorus_invoice_format = fields.Selection(
        [], string='Chorus Invoice Format')
    fr_chorus_check_commitment_number = fields.Boolean(
        string='Check Commitment Numbers',
        help="If enabled, Odoo will check the commitment number "
        "('engagement juridique' in French) upon invoice validation. "
        "It corresponds to the 'customer order reference' in "
        "the administrative tongue. "
        "It will also check it upon sale order validation if the module "
        "l10n_fr_chorus_sale is installed.")
    fr_chorus_pwd_expiry_date = fields.Date(
        string='Chorus Technical User Password Expiry Date')
    fr_chorus_expiry_remind_user_ids = fields.Many2many(
        'res.users', 'fr_chorus_api_expiry_remind_user_rel',
        'company_id', 'user_id', string='Users Receiving the Expiry Reminder')

    @property
    def _server_env_fields(self):
        env_fields = super()._server_env_fields
        env_fields.update({
            "fr_chorus_api_login": {},
            "fr_chorus_api_password": {},
            "fr_chorus_qualif": {},
        })
        return env_fields

    def chorus_get_piste_api_oauth_identifiers(self, raise_if_ko=False):
        """Inherit this method if you want to configure your Chorus certificates
        elsewhere or have per-company Chorus certificates"""
        self.ensure_one()
        oauth_id = tools.config.get('chorus_api_oauth_id')
        oauth_secret = tools.config.get('chorus_api_oauth_secret')
        if not oauth_id:
            msg = _(
                "Missing key 'chorus_api_oauth_id' in Odoo server "
                "configuration file")
            if raise_if_ko:
                raise UserError(msg)
            else:
                logger.warning(msg)
                return False
        if not oauth_secret:
            msg = _(
                "Missing key 'chorus_api_oauth_secret' in Odoo server "
                "configuration file")
            if raise_if_ko:
                raise UserError(msg)
            else:
                logger.warning(msg)
                return False
        return (oauth_id, oauth_secret)

    def chorus_get_api_params(self, raise_if_ko=False):
        self.ensure_one()
        api_params = {}
        oauth_identifiers = self.chorus_get_piste_api_oauth_identifiers(
            raise_if_ko=raise_if_ko)
        if (
                self.fr_chorus_invoice_format and
                self.fr_chorus_api_login and
                self.fr_chorus_api_password and
                oauth_identifiers):
            api_params = {
                'login': self.fr_chorus_api_login,
                'password': self.fr_chorus_api_password,
                'qualif': self.fr_chorus_qualif,
                'oauth_id': oauth_identifiers[0],
                'oauth_secret': oauth_identifiers[1],
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
                self.fr_chorus_pwd_expiry_date and
                self.fr_chorus_pwd_expiry_date < today):
            if raise_if_ko:
                raise UserError(_(
                    "The expiry date of the technical user password for "
                    "Chorus API is %s. You should login to Chorus Pro, "
                    "generate a new password for the technical user and "
                    "update it in the menu Accounting > Configuration > "
                    "Configuration.")
                    % self.fr_chorus_pwd_expiry_date)
            else:
                logger.warning(
                    "The Chorus Pro technical user password expired on %s",
                    self.fr_chorus_pwd_expiry_date)
        return api_params

    @api.model
    @tools.ormcache("oauth_id", "oauth_secret", "qualif")
    def _get_new_token(self, oauth_id, oauth_secret, qualif):
        url = qualif and QUALIF_TOKEN_URL or TOKEN_URL
        logger.info('Requesting new token from PISTE via %s', url)
        try:
            r = requests.post(
                url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": oauth_id,
                    "client_secret": oauth_secret,
                    "scope": "openid"
                    })
            logger.debug('_get_new_token HTTP answer code=%s', r.status_code)
        except requests.exceptions.ConnectionError as e:
            logger.error("Connection to %s failed. Error: %s", url, e)
            raise UserError(_(
                "Connection to PISTE (URL %s) failed. "
                "Check the internet connection of the Odoo server.\n\n"
                "Error details: %s") % (url, e))
        except requests.exceptions.RequestException as e:
            logger.error("PISTE request for new token failed. Error: %s", e)
            raise UserError(_(
                "Technical failure when trying to get a new token "
                "from PISTE.\n\nError details: %s") % e)
        try:
            token = r.json()
        except Exception:
            logger.error("JSON decode failed. HTTP error code: %s." % r.status_code)
            raise UserError(_(
                "Error in the request to get a new token via PISTE. "
                "HTTP error code: %s.") % r.status_code)
        if r.status_code != 200:
            logger.error(
                'Error %s in the request to get a new token. '
                'Error type: %s. Error description: %s',
                r.status_code, token.get('error'),
                token.get('error_description'))
            raise UserError(_(
                "Error in the request to get a new token via PISTE.\n\n"
                "HTTP error code: %s. Error type: %s. "
                "Error description: %s.") % (
                    r.status_code, token.get('error'),
                    token.get('error_description')))
        # {'access_token': 'xxxxxxxxxxxxxxxxx',
        # 'token_type': 'Bearer', 'expires_in': 3600, 'scope': 'openid'}
        logger.info(
            'New token retreived with a validity of '
            '%d seconds', token.get('expires_in'))
        seconds = int(token.get('expires_in')) - MARGIN_TOKEN_EXPIRY_SECONDS
        expiry_date_gmt = datetime.utcnow() + timedelta(seconds=seconds)
        return (token, expiry_date_gmt)

    def _get_token(self, api_params):
        token, expiry_date_gmt = self._get_new_token(
            api_params['oauth_id'], api_params['oauth_secret'],
            api_params['qualif'])
        now = datetime.utcnow()
        logger.debug('_get_token expiry_date_gmt=%s now=%s', expiry_date_gmt, now)
        if now > expiry_date_gmt:
            # force clear cache
            self._get_new_token.clear_cache(self.env[self._name])
            logger.info('PISTE Token cleared from cache.')
            token, expiry_date_gmt = self._get_new_token(
                api_params['oauth_id'], api_params['oauth_secret'],
                api_params['qualif'])
        else:
            logger.info(
                'PISTE token expires on %s GMT (includes margin)',
                expiry_date_gmt)
        return token

    @api.model
    def chorus_post(self, api_params, url_path, payload, session=None):
        url_base = api_params['qualif'] and QUALIF_API_URL or API_URL
        url = '%s/cpro/%s' % (url_base, url_path)
        auth = (api_params['login'], api_params['password'])
        auth_piste = '%s:%s' % auth
        auth_piste_b64 = base64.b64encode(auth_piste.encode('utf8'))
        headers = {
            'Content-type': 'application/json',
            'cpro-account': auth_piste_b64,
            'Authorization': 'Bearer',
            }
        if session is None:
            token = self._get_token(api_params)
            session = OAuth2Session(api_params['oauth_id'], token=token)
        logger.info(
            'Chorus API POST request to %s with login %s',
            url, api_params['login'])
        logger.info('Payload of the Chorus POST request: %s', payload)
        try:
            r = session.post(
                url, verify=True, data=json.dumps(payload),
                headers=headers)
        except requests.exceptions.ConnectionError as e:
            logger.error("Connection to %s failed. Error: %s", url, e)
            raise UserError(_(
                "Connection to Chorus API (URL %s) failed. "
                "Check the Internet connection of the Odoo server.\n\n"
                "Error details: %s") % (url, e))
        except requests.exceptions.RequestException as e:
            logger.error("Chorus POST request failed. Error: %s", e)
            raise UserError(_(
                "Technical failure when trying to connect to Chorus API.\n\n"
                "Error details: %s") % e)
        if r.status_code != 200:
            logger.error(
                "Chorus API webservice answered with HTTP status code=%s and "
                "content=%s" % (r.status_code, r.text))
            raise UserError(_(
                "Wrong request on %s. HTTP error code received from "
                "Chorus: %s") % (url, r.status_code))

        answer = r.json()
        logger.info('Chorus WS answer payload: %s', answer)
        return (answer, session)

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
            ('fr_chorus_pwd_expiry_date', '!=', False),
            ('fr_chorus_pwd_expiry_date', '<=', limit_date),
            ])
        mail_tpl = self.env.ref(
            'l10n_fr_chorus_account.chorus_api_expiry_reminder_mail_template')
        for company in companies:
            if company.fr_chorus_expiry_remind_user_ids:
                expiry_date_dt = fields.Date.from_string(
                    company.fr_chorus_pwd_expiry_date)
                pwd_days = (expiry_date_dt - today_dt).days
                mail_tpl.with_context(pwd_days=pwd_days).send_mail(company.id)
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

    def _check_chorus_invoice_format(self):
        """Inherited in some invoice-format-specific modules
        e.g. l10n_fr_chorus_facturx"""
        self.ensure_one()
