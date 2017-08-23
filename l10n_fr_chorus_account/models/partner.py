# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # On commercial partner only
    fr_chorus_required = fields.Selection([
        ('none', 'None'),
        ('service', 'Service'),
        ('engagement', 'Engagement'),
        # better to use a bad English translation of the French word!
        ('service_or_engagement', u'Service or Engagement'),
        ('service_and_engagement', u'Service and Engagement'),
        ], string='Info Required for Chorus', track_visibility='onchange')
    # On contact partner only
    fr_chorus_service_code = fields.Char(
        string='Chorus Service Code', size=100, track_visibility='onchange',
        help='Service Code may be required for Chorus invoices')
