# -*- coding: utf-8 -*-
# © 2014-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    @api.depends('zip', 'country_id', 'country_id.code')
    # If a department code changes, it will have to be manually recomputed
    def _compute_department(self):
        rcdo = self.env['res.country.department']
        fr_country_ids = self.env['res.country'].search([
            ('code', 'in', ('FR', 'GP', 'MQ', 'GF', 'RE', 'YT'))]).ids
        for partner in self:
            dpt_id = False
            zip = partner.zip
            if (
                    partner.country_id and
                    partner.country_id.id in fr_country_ids and
                    zip and
                    len(zip) == 5):
                code = zip[0:2]
                if code == '97':
                    code = zip[0:3]
                dpts = rcdo.search([
                    ('code', '=', code),
                    ('country_id', 'in', fr_country_ids),
                    ])
                if len(dpts) == 1:
                    dpt_id = dpts[0].id
            partner.department_id = dpt_id

    department_id = fields.Many2one(
        'res.country.department', compute='_compute_department',
        string='Department', readonly=True, store=True)
