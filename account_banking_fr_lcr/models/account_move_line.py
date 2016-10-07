# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.multi
    def _prepare_payment_line_vals(self, payment_order):
        vals = super(AccountMoveLine, self)._prepare_payment_line_vals(
            payment_order)
        if payment_order.payment_mode_id.payment_method_id.code == 'fr_lcr':
            # Take the first IBAN account of the partner
            bank_accounts = self.env['res.partner.bank'].search([
                ('partner_id', '=', self.partner_id.id),
                ('acc_type', '=', 'iban'),
                ])
            if bank_accounts:
                vals['partner_bank_id'] = bank_accounts[0].id
        return vals
