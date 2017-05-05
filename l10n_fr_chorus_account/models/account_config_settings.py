# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    fr_vat_scheme = fields.Selection(
        related='company_id.partner_id.fr_vat_scheme')
