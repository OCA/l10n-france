# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from openerp import models, fields


class PublicMarket(models.Model):
    _inherit = 'public.market'

    sale_ids = fields.One2many(
        'sale.order', 'public_market_id', string='Sale Orders', readonly=True,
        domain=[('state', 'not in', ('draft', 'sent', 'cancel'))])
