# -*- coding: utf-8 -*-

# © 2018 Le Filament (<http://www.le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import requests

from odoo import api, fields, models

URL = "https://data.opendatasoft.com/api/records/1.0/"\
    "search/?dataset=sirene_v3%40public&q={request}&rows=100"


class SirenWizard(models.TransientModel):
    _name = 'siren.wizard'
    _description = 'Get values from companies'

    # Default functions
    @api.model
    def _default_name(self):
        return self.env['res.partner'].browse(
            self.env.context.get('active_id')).name

    @api.model
    def _default_partner(self):
        return self.env.context.get('active_id')

    # Fields
    name = fields.Char(string='Company', default=_default_name)
    line_ids = fields.One2many('siren.wizard.line', 'wizard_id',
                               string="Results")
    partner_id = fields.Integer('Partner', default=_default_partner)

    # Action
    @api.model
    def _prepare_partner_from_data(self, data):
        return {
            'name': data.get('denominationunitelegale'),
            'street': data.get('adresseetablissement', False),
            'zip': data.get('codepostaletablissement', False),
            'city': data.get('libellecommuneetablissement', False),
            'siren': data.get('siren', False),
            'siret': data.get('siret', False),
            'category': data.get('categorieentreprise', False),
            'creation_date': data.get('datecreationunitelegale', False),
            'ape': data.get('activiteprincipaleunitelegale', False),
            'ape_label': data.get('divisionunitelegale', False),
            'legal_type': data.get('naturejuridiqueunitelegale', False),
            'staff': data.get('trancheeffectifsunitelegale', 0),
        }

    def get_lines(self):
        # Get request
        r = requests.get(URL.format(request=self.name))
        # Serialization request to JSON
        companies = r.json()
        # Fill new company lines
        companies_vals = []
        for company in companies['records']:
            res = self._prepare_partner_from_data(company['fields'])
            companies_vals.append((0, 0, res))
        self.line_ids.unlink()
        self.line_ids = companies_vals
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'siren.wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
