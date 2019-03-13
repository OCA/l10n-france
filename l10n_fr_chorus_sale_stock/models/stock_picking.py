# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _get_invoice_vals(self, key, inv_type, journal_id, move):
        inv_vals = super(StockPicking, self)._get_invoice_vals(
            key, inv_type, journal_id, move)
        sale = move.picking_id.sale_id
        if (
                sale and
                sale.public_market_id and
                inv_type in ('out_invoice', 'out_refund')):
            inv_vals['public_market_id'] = sale.public_market_id.id
        return inv_vals
