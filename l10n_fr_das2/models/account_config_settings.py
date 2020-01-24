# -*- coding: utf-8 -*-
# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    fr_das2_partner_declare_threshold = fields.Monetary(
        related='company_id.fr_das2_partner_declare_threshold', readonly=False)
