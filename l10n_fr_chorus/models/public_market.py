# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from openerp import models, fields, api


class PublicMarket(models.Model):
    _name = 'public.market'
    _description = 'Public Market Reference'
    _rec_name = 'display_name'

    code = fields.Char(
        string='Market Number', required=True, copy=False, size=50)
    name = fields.Char(string='Market Name', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env['res.company']._company_default_get(
            'public.market'))
    active = fields.Boolean(string='Active', default=True)
    display_name = fields.Char(
        compute='compute_display_name_field',
        readonly=True, store=True)

    @api.multi
    @api.depends('code', 'name')
    def compute_display_name_field(self):
        for market in self:
            market.display_name = u'[%s] %s' % (market.code, market.name)

    _sql_constraints = [(
        'code_company_unique',
        'unique(code, company_id)',
        'This public market number already exists!'
        )]
