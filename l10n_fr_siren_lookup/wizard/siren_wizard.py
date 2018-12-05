# -*- coding: utf-8 -*-

# © 2018 Le Filament (<http://www.le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import requests

from odoo import api, fields, models

URL = "https://data.opendatasoft.com/api/records/1.0/"\
    "search/?dataset=sirene%40public&q={request}&rows=100"


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
            'name': data.get('l1_normalisee'),
            'street': data.get('l4_normalisee', False),
            'zip': data.get('codpos', False),
            'city': data.get('libcom', False),
            'siren': data.get('siren', False),
            'siret': data.get('siret', False),
            'category': data.get('categorie', False),
            'creation_date': data.get('dcret', False),
            'ape': data.get('apen700', False),
            'ape_label': data.get('libapet', False),
            'legal_type': data.get('libnj', False),
            'staff': data.get('efetcent', 0),
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
        self.line_ids = companies_vals
        return {"type": "ir.actions.do_nothing", }
