# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api


class SaleOrderLineMakeInvoice(models.TransientModel):
    _inherit = 'sale.order.line.make.invoice'

    @api.model
    def _prepare_invoice(self, order, lines):
        vals = super(SaleOrderLineMakeInvoice, self)._prepare_invoice(
            order, lines)
        if order.public_market_id:
            vals['public_market_id'] = order.public_market_id.id
        return vals
