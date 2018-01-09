# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.tools.config import config


class PosConfig(models.Model):
    _inherit = 'pos.config'

    _SELECTION_HASH_PRINT = [
        ('no', 'Default behaviour'),
        ('normal_or_block', 'Do not Print Hash or Prevent Printing'),
        ('hash_or_warning', 'Print Hash or Mark a Warning'),
        ('hash_or_block', 'Print Hash or Prevent Printing'),
    ]

    _SELECTION_HASH_PRINT_LEGACY = [
        ('normal_or_block', 'Do not Print Hash or Prevent Printing'),
        ('hash_or_warning', 'Print Hash or Mark a Warning'),
        ('hash_or_block', 'Print Hash or Prevent Printing'),
    ]

    l10n_fr_is_accounting_unalterable = fields.Boolean(
        compute='_compute_l10n_fr_is_accounting_unalterable')

    l10n_fr_prevent_print = fields.Selection(
        string='Prevent Uncertified Bill (Fixed Value)',
        selection=_SELECTION_HASH_PRINT,
        compute='_compute_l10n_fr_prevent_print',
        help="Indicate what is the behaviour of the Point of Sale, if"
        " the server is unreachable. The value has been fixed by your"
        " Odoo host administrator. You should contact him if you want to"
        " change the value.")

    l10n_fr_prevent_print_server = fields.Char(
        string='Prevent Uncertified Bill (Server Value)',
        compute='_compute_l10n_fr_prevent_print_server')

    l10n_fr_prevent_print_legacy = fields.Selection(
        string='Prevent Uncertified Bill',
        selection=_SELECTION_HASH_PRINT_LEGACY, help="Indicate what is the"
        " behaviour of the Point of Sale, regarding French Certification:\n\n"
        " * 'Do not Print Hash or Prevent Printing':\n"
        " -> In normal mode (online), normal bill is printed\n"
        " -> in downgraded mode (offline), bill printing is disabled\n\n"
        " * 'Print Hash or Mark a Warning':\n"
        " -> In normal mode (online), the hash is printed\n"
        " -> in downgraded mode (offline), a warning is printed\n\n"
        " * 'Print Hash or Prevent Printing':\n"
        " -> In normal mode (online), the hash is printed\n"
        " -> in downgraded mode (offline), bill printing is disabled\n\n"
        " Disabling printing is the most secure mode from a point of view"
        " of certification but you have to ensure that network connection"
        " is reliable")

    # Compute Section
    def _compute_l10n_fr_is_accounting_unalterable(self):
        for pos_config in self:
            pos_config.l10n_fr_is_accounting_unalterable =\
                pos_config.company_id._is_accounting_unalterable()

    def _compute_l10n_fr_prevent_print_server(self):
        file_value = config.get('l10n_fr_certification_mode', 'legacy')
        for pos_config in self:
            pos_config.l10n_fr_prevent_print_server = file_value

    @api.depends(
        'l10n_fr_prevent_print_server', 'l10n_fr_prevent_print_legacy')
    def _compute_l10n_fr_prevent_print(self):
        for pos_config in self:
            if not pos_config.l10n_fr_is_accounting_unalterable:
                pos_config.l10n_fr_prevent_print = 'no'
                continue
            server_value = pos_config.l10n_fr_prevent_print_server
            if server_value == 'legacy':
                if not pos_config.l10n_fr_prevent_print_legacy:
                    pos_config.l10n_fr_prevent_print = 'no'
                else:
                    pos_config.l10n_fr_prevent_print =\
                        pos_config.l10n_fr_prevent_print_legacy
            else:
                pos_config.l10n_fr_prevent_print = server_value
