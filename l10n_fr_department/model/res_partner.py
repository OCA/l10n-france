# -*- encoding: utf-8 -*-
##############################################################################
#
#    l10n FR Departments module for OpenERP
#    Copyright (C) 2014 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.one
    @api.depends('zip', 'country_id', 'country_id.code')
    # If a department code changes, it will have to be manually recomputed
    def _compute_department(self):
        '''This method is designed to be inherited'''
        dpt_id = False
        zip = self.zip
        if (
                self.country_id and
                self.country_id.code == 'FR' and
                zip and
                len(zip) == 5):
            code = zip[0:2]
            dpts = self.env['res.country.department'].search([
                ('code', '=', code),
                ('country_id', '=', self.country_id.id),
                ])
            if len(dpts) == 1:
                dpt_id = dpts[0].id
        self.department_id = dpt_id

    department_id = fields.Many2one(
        'res.country.department', compute='_compute_department',
        string='Department', readonly=True, store=True)
