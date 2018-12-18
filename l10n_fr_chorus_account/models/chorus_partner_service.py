# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class ChorusPartnerService(models.Model):
    _name = 'chorus.partner.service'
    _description = 'Chorus Services attached to a partner'
    _order = 'partner_id, code'

    partner_id = fields.Many2one(
        'res.partner', string='Customer', ondelete='cascade',
        domain=[('parent_id', '=', False)])
    code = fields.Char(string='Service Code', required=True)
    active = fields.Boolean(default=True)
    name = fields.Char(string='Service Name')
    chorus_identifier = fields.Integer(readonly=True)

    @api.depends('code', 'name')
    def name_get(self):
        res = []
        for partner in self:
            name = u'[%s] %s' % (partner.code, partner.name or '-')
            res.append((partner.id, name))
        return res

    _sql_constraints = [
        ('partner_code_uniq',
         'unique(partner_id, code)',
         'This Chorus service code already exists for that partner!'),
        # the chorus_identifier seems global and not per partner
        ('chorus_identifier_uniq',
         'unique(chorus_identifier)',
         'This service Chorus identifier already exists!')]

    @api.model
    def name_search(
            self, name='', args=None, operator='ilike', limit=80):
        if args is None:
            args = []
        if name:
            srvs = self.search(
                [('code', '=', name)] + args, limit=limit)
            if srvs:
                return srvs.name_get()
            srvs = self.search(
                ['|', ('code', 'ilike', name), ('name', 'ilike', name)] + args,
                limit=limit)
            if srvs:
                return srvs.name_get()
        return super(ChorusPartnerService, self).name_search(
            name=name, args=args, operator=operator, limit=limit)
