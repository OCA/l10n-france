# -*- coding: utf-8 -*-

# © 2018 Le Filament (<http://www.le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class SirenWizardLine(models.TransientModel):
    _name = 'siren.wizard.line'
    _description = 'Company Selection'

    # Fields
    wizard_id = fields.Many2one('siren.wizard', string='Wizard',)
    name = fields.Char(string='Name')
    street = fields.Char(string='Street')
    zip = fields.Char(string='CP')
    city = fields.Char(string='City')

    legal_type = fields.Char("Legal Type")
    siren = fields.Char("SIREN")
    siret = fields.Char("SIRET")
    ape = fields.Char("APE Code")
    ape_label = fields.Char("APE Label")
    creation_date = fields.Date("Creation date")
    staff = fields.Char("# Staff")
    category = fields.Char("Category")

    # Action
    @api.multi
    def update_partner(self):
        partner = self.env['res.partner'].browse(self.wizard_id.partner_id)
        partner.write({
            'name': self.name,
            'street': self.street,
            'zip': self.zip,
            'city': self.city,
            'legal_type': self.legal_type,
            'siren': self.siren,
            'siret': self.siret,
            'ape': self.ape,
            'ape_label': self.ape_label,
            'creation_date': self.creation_date,
            'staff': self.staff,
            'category': self.category,
        })
