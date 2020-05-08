# -*- coding: utf-8 -*-
# Copyright 2017-2020 Akretion France (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    group_chorus_api = fields.Selection([
        (0, 'Do not use Chorus API'),
        (1, 'Use Chorus API via PISTE'),
        ], string='Use Chorus API',
        implied_group='l10n_fr_chorus_account.group_chorus_api',
        help="If you select 'Use Chorus API', it will add all users to the "
        "Chorus API group.")
    fr_chorus_api_login = fields.Char(
        related='company_id.fr_chorus_api_login', readonly=False)
    fr_chorus_api_password = fields.Char(
        related='company_id.fr_chorus_api_password', readonly=False)
    fr_chorus_qualif = fields.Boolean(
        related='company_id.fr_chorus_qualif', readonly=False)
    fr_chorus_invoice_format = fields.Selection(
        related='company_id.fr_chorus_invoice_format', readonly=False)
    fr_chorus_pwd_expiry_date = fields.Date(
        related='company_id.fr_chorus_pwd_expiry_date', readonly=False)
    fr_chorus_expiry_remind_user_ids = fields.Many2many(
        related='company_id.fr_chorus_expiry_remind_user_ids', readonly=False)
