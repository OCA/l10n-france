# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


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
    # On contact partner only
    fr_chorus_service_code = fields.Char(
        string='Chorus Service Code', size=100, track_visibility='onchange',
        help='Service Code may be required for Chorus invoices')

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
        for partner in self:
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

    def fr_chorus_identifier_and_required_button(self):
        self.fr_chorus_identifier_get()
        self.fr_chorus_required_get()
        return
