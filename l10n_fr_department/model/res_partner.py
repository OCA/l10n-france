# Copyright 2014-2018 Akretion France
# author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('zip', 'country_id', 'country_id.code')
    # If a department code changes, it will have to be manually recomputed
    def _compute_department(self):
        rcdo = self.env['res.country.department']
        fr_country_ids = self.env['res.country'].search([
            ('code', 'in', ('FR', 'GP', 'MQ', 'GF', 'RE', 'YT'))]).ids
        for partner in self:
            dpt_id = False
            zipcode = partner.zip
            if (
                    partner.country_id and
                    partner.country_id.id in fr_country_ids and
                    zipcode and
                    len(zipcode) == 5):
                zipcode = partner.zip.strip().replace(' ', '').rjust(5, '0')
                code = zipcode[0:2]
                if code == '97':
                    code = zipcode[0:3]
                if code == '20':
                    code = self._compute_department_corsica(zipcode)
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

    def _compute_department_corsica(self, zipcode):
        try:
            zipcode = int(zipcode)
        except ValueError:
            return '20'
        if 20000 <= zipcode < 20200:
            # Corse du Sud / 2A
            code = '2A'
        elif 20200 <= zipcode <= 20620:
            code = '2B'
        else:
            code = '20'
        return code
