# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    group_chorus_api = fields.Selection([
        (0, 'Do not use Chorus API'),
        (1, 'Use Chorus API (requires RGS 1* certificate)'),
        ], string='Use Chorus API',
        implied_group='l10n_fr_chorus_account.group_chorus_api',
        help="If you select 'Use Chorus API', it will add all users to the "
        "Chorus API group.")
    fr_chorus_api_login = fields.Char(
        related='company_id.fr_chorus_api_login')
    fr_chorus_api_password = fields.Char(
        related='company_id.fr_chorus_api_password')
    fr_chorus_qualif = fields.Boolean(
        related='company_id.fr_chorus_qualif')
    fr_chorus_invoice_format = fields.Selection(
        related='company_id.fr_chorus_invoice_format')
