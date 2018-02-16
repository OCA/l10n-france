# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models, _
from odoo.exceptions import UserError
import requests
import json
import logging
logger = logging.getLogger(__name__)


class ChorusApi(models.AbstractModel):
    _name = 'chorus.api'
    _description = 'Chorus API'

    @api.model
    def chorus_post(self, api_params, url_path, payload, session=None):
        url_base = 'https://chorus-pro.gouv.fr:5443'
        service = api_params['qualif'] and 'service-qualif' or 'service'
        url = '%s/%s/%s' % (url_base, service, url_path)
        auth = (api_params['login'], api_params['password'])
        if session is None:
            session = requests.Session()
            session.cert = api_params['cert']
        logger.info('Chorus API POST request to %s', url)
        logger.info('Payload of the Chorus POST request: %s', payload)
        try:
            r = session.post(
                url, verify=True, data=json.dumps(payload), auth=auth)
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
                "Chorus API webservice answered with HTTP status code=%s"
                % r.status_code)
            raise UserError(_(
                "Wrong request on %s. HTTP error code received from "
                "Chorus: %s") % (url, r.status_code))

        answer = r.json()
        logger.info('Chorus WS answer payload: %s', answer)
        return (answer, session)
