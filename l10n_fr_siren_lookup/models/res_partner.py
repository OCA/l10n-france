# -*- coding: utf-8 -*-

# © 2018 Le Filament (<http://www.le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Fields
    legal_type = fields.Char("Legal Type")
    siren = fields.Char("SIREN")
    siret = fields.Char("SIRET")
    ape = fields.Char("APE Code")
    ape_label = fields.Char("APE Label")
    creation_date = fields.Date("Creation date")
    staff = fields.Char("# Staff")
    category = fields.Char("Category")
