# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    @api.multi
    def _prepare_advance_invoice_vals(self):
        result = super(
            SaleAdvancePaymentInv, self)._prepare_advance_invoice_vals()
        for (sale_id, vals) in result:
            order = self.env['sale.order'].browse(sale_id)
            if order.public_market_id.id:
                vals['public_market_id'] = order.public_market_id.id
        return result
