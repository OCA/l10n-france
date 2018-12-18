# -*- coding: utf-8 -*-
# Copyright 2017-2018 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'chorus.api']

    # On commercial partner only
    fr_chorus_required = fields.Selection([
        ('none', 'None'),
        ('service', 'Service'),
        ('engagement', 'Engagement'),
        # better to use a bad English translation of the French word!
        ('service_or_engagement', u'Service or Engagement'),
        ('service_and_engagement', u'Service and Engagement'),
        ], string='Info Required for Chorus', track_visibility='onchange')
    fr_chorus_identifier = fields.Integer('Chorus Identifier', readonly=True)
    fr_chorus_service_count = fields.Integer(
        compute='_compute_fr_chorus_service_count', readonly=True,
        string='Number of Chorus Services')
    # On contact partner only
    fr_chorus_service_id = fields.Many2one(
        'chorus.partner.service', string='Chorus Service',
        ondelete='restrict')
    fr_chorus_service_code = fields.Char(
        string='Chorus Service Code', size=100, track_visibility='onchange',
        help='Service Code may be required for Chorus invoices')

    def _compute_fr_chorus_service_count(self):
        res = self.env['chorus.partner.service'].read_group(
            [('partner_id', 'in', self.ids)], ['partner_id'], ['partner_id'])
        for re in res:
            partner = self.browse(re['partner_id'][0])
            partner.fr_chorus_service_count = re['partner_id_count']

    @api.constrains('fr_chorus_service_code', 'name', 'parent_id')
    def check_fr_chorus_service_code(self):
        for partner in self:
            if partner.fr_chorus_service_code and not partner.parent_id:
                raise ValidationError(_(
                    "Chorus service codes can only be set on contacts, "
                    "not on parent partners. Chorus service code '%s' has "
                    "been set on partner %s that has no parent.")
                    % (partner.fr_chorus_service_code, partner.display_name))
            if partner.fr_chorus_service_code and not partner.name:
                raise ValidationError(_(
                    "Contacts with a Chorus service code should have a name. "
                    "The Chorus service code '%s' has been set on a contact "
                    "without a name.") % partner.fr_chorus_service_code)
            if partner.fr_chorus_service_id:
                if not partner.fr_chorus_service_code:
                    raise ValidationError(_(
                        "The contact '%s' has a link to a Chorus Service "
                        "but its Chorus Service Code is not set.")
                        % partner.display_name)
                elif (
                        partner.fr_chorus_service_code !=
                        partner.fr_chorus_service_id.code):
                    raise ValidationError(_(
                        "The contact '%s' has a link to Chorus Service "
                        "'%s' but its Chorus Service Code has a different "
                        "value (%s).") % (
                            partner.display_name,
                            partner.fr_chorus_service_id.display_name,
                            partner.fr_chorus_service_code))

    @api.onchange('fr_chorus_service_id')
    def fr_chorus_service_id_change(self):
        if self.fr_chorus_service_id:
            self.fr_chorus_service_code = self.fr_chorus_service_id.code

    def fr_chorus_api_structures_rechercher(self, api_params, session=None):
        url_path = 'structures/rechercher'
        payload = {
            'structure': {
                'identifiantStructure': self.siret,
                'typeIdentifiantStructure': 'SIRET',
                },
            }
        answer, session = self.chorus_post(
            api_params, url_path, payload, session=session)
        res = False
        # from pprint import pprint
        # pprint(answer)
        if (
                answer.get('listeStructures') and
                len(answer['listeStructures']) == 1 and
                answer['listeStructures'][0].get('idStructureCPP')):
            res = answer['listeStructures'][0]['idStructureCPP']
        return (res, session)

    def fr_chorus_identifier_get(self):
        api_params = self.env.user.company_id.chorus_get_api_params(
            raise_if_ko=True)
        for partner in self:
            if partner.parent_id:
                raise UserError(_(
                    "Cannot get Chorus Identifier on a contact (%s)")
                    % partner.display_name)
            if not partner.nic or not partner.siren:
                raise UserError(_(
                    "Missing SIRET on partner %s") % partner.display_name)
        session = None
        for partner in self.filtered(lambda p: not p.fr_chorus_identifier):
            (res, session) = partner.fr_chorus_api_structures_rechercher(
                api_params, session)
            if res:
                partner.fr_chorus_identifier = res
            else:
                raise UserError(_(
                    "No entity found in Chorus corresponding to SIRET %s. "
                    "The detailed error is written in Odoo server logs.")
                    % partner.siret)

    def fr_chorus_api_structures_consulter(self, api_params, session):
        url_path = 'structures/consulter'
        payload = {'idStructureCPP': self.fr_chorus_identifier}
        answer, session = self.chorus_post(
            api_params, url_path, payload, session=session)
        res = False
        # from pprint import pprint
        # pprint(answer)
        if answer.get('parametres'):
            if answer['parametres'].get('gestionNumeroEJOuCodeService'):
                res = 'service_or_engagement'
            elif (
                    answer['parametres'].get(
                        'codeServiceDoitEtreRenseigne') and
                    answer['parametres'].get('numeroEJDoitEtreRenseigne')):
                res = 'service_and_engagement'
            elif answer['parametres'].get('codeServiceDoitEtreRenseigne'):
                res = 'service'
            elif answer['parametres'].get('numeroEJDoitEtreRenseigne'):
                res = 'engagement'
            else:
                res = 'none'
        return (res, session)

    def fr_chorus_required_get(self):
        api_params = self.env.user.company_id.chorus_get_api_params(
            raise_if_ko=True)
        for partner in self:
            if not partner.fr_chorus_identifier:
                raise UserError(_(
                    "Missing Chorus Identifier on partner %s")
                    % partner.display_name)
        session = None
        for partner in self:
            (res, session) = partner.fr_chorus_api_structures_consulter(
                api_params, session)
            if res:
                partner.fr_chorus_required = res

    def fr_chorus_api_rechercher_services(self, api_params, session):
        url_path = 'structures/rechercher/services'
        payload = {
            'idStructure': self.fr_chorus_identifier,
            'parametresRechercherServicesStructure':
                {'nbResultatsParPage': 10000},
            }
        answer, session = self.chorus_post(
            api_params, url_path, payload, session=session)
        res = {}
        # from pprint import pprint
        # pprint(answer)
        if (
                answer.get('codeRetour') == 0 and
                answer.get('listeServices') and
                isinstance(answer['listeServices'], list)):
            for srv in answer['listeServices']:
                if srv.get('idService') and srv.get('codeService'):
                    res[int(srv['idService'])] = {
                        'code': srv['codeService'],
                        'name': srv.get('libelleService'),
                        'active': srv.get('estActif'),
                        }
# answer: {u'codeRetour': 0,
# u'libelle': u'TRA_MSG_00.000',
# u'listeServices': [{u'codeService': u'XX',
#                     u'dateDbtService': u'2016-10-25 17:42',
#                     u'dateFinService': u'2050-12-31 00:00',
#                     u'estActif': True,
#                     u'idService': 27946199,
#                     u'libelleService': u'CODE SERVICE INCONNU'},
#                    {u'codeService': u'W9',
#                     u'dateDbtService': u'2016-10-25 17:40',
#                     u'dateFinService': u'2050-12-31 00:00',
#                     u'estActif': True,
#                     u'idService': 27946194,
#                     u'libelleService': u'Murielle ANDRE'},
# [...]
# u'parametresRetour': {u'nbResultatsParPage': 10,
#                       u'pageCourante': 1,
#                       u'pages': 22,
#                       u'total': 218}}
        return (res, session)

    def fr_chorus_services_get(self):
        api_params = self.env.user.company_id.chorus_get_api_params(
            raise_if_ko=True)
        for partner in self:
            if not partner.fr_chorus_identifier:
                raise UserError(_(
                    "Missing Chorus Identifier on partner %s.")
                    % partner.display_name)
            if not partner.fr_chorus_required:
                raise UserError(_(
                    "Missing Info Required for Chorus on partner %s.")
                    % partner.display_name)
        session = None
        cpso = self.env['chorus.partner.service']
        for partner in self.filtered(
                lambda p: p.fr_chorus_required in
                ('service', 'service_or_engagement',
                 'service_and_engagement')):
            (res, session) = partner.fr_chorus_api_rechercher_services(
                api_params, session)
            if res:
                # from pprint import pprint
                # pprint(res)
                logger.info(
                    'Starting to update Chorus services of partner %s ID %d',
                    partner.display_name, partner.id)
                existing_res = {}
                existing_srvs = cpso.search_read(
                    [('partner_id', '=', partner.id)],
                    ['code', 'name', 'chorus_identifier', 'active'])
                for existing_srv in existing_srvs:
                    existing_res[existing_srv['chorus_identifier']] = {
                        'id': existing_srv['id'],
                        'name': existing_srv['name'],
                        'code': existing_srv['code'],
                        'active': existing_srv['active'],
                        }
                # pprint(existing_res)
                for chorus_identifier, cdata in res.items():
                    if existing_res.get(chorus_identifier):
                        existing_p = existing_res[chorus_identifier]
                        if (
                                existing_p.get('name') != cdata.get('name') or
                                existing_p.get('code') != cdata.get('code') or
                                existing_p.get('active') !=
                                cdata.get('active')):
                            partner_service = cpso.browse(existing_p['id'])
                            partner_service.write(cdata)
                            logger.info(
                                'Chorus partner service ID %d with Chorus '
                                'identifier %s updated',
                                existing_p['id'], chorus_identifier)
                        else:
                            logger.info(
                                'Chorus partner service ID %d with Chorus '
                                'identifier %s kept unchanged',
                                existing_p['id'], chorus_identifier)
                    else:
                        partner_service = cpso.create({
                            'partner_id': partner.id,
                            'code': cdata.get('code'),
                            'name': cdata.get('name'),
                            'active': cdata.get('active'),
                            'chorus_identifier': chorus_identifier,
                            })
                        logger.info(
                            'Chorus partner service with Chorus identifier %s '
                            'created (ID %d)',
                            chorus_identifier, partner_service.id)

    def fr_chorus_identifier_and_required_button(self):
        self.fr_chorus_identifier_get()
        self.fr_chorus_required_get()
        self.fr_chorus_services_get()
        return
