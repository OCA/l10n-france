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

from openerp.osv import orm, fields


class res_partner(orm.Model):
    _inherit = 'res.partner'

    def _get_departement_of_partner(self, cr, uid, partner, context=None):
        '''This method is designed to be inherited'''
        dpt_id = False
        zip = partner.zip
        if (
                partner.country_id
                and partner.country_id.code == 'FR'
                and zip
                and len(zip) == 5):
            code = zip[0:2]
            dpt_ids = self.pool['res.country.department'].search(
                cr, uid, [
                    ('code', '=', code),
                    ('country_id', '=', partner.country_id.id),
                    ], context=context)
            if len(dpt_ids) == 1:
                dpt_id = dpt_ids[0]
        return dpt_id

    def _compute_department(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids, context=context):
            res[partner.id] = self._get_departement_of_partner(
                cr, uid, partner, context=context)
        return res

    def _get_partner_from_department(self, cr, uid, ids, context=None):
        # Recompute all partners with zip and country
        partner_ids = self.pool['res.partner'].search(
            cr, uid, [
                '|', ('active', '=', True), ('active', '=', False),
                ('zip', '!=', False), ('country_id', '!=', False)],
            context=context)
        return partner_ids

    _columns = {
        'department_id': fields.function(
            _compute_department, type='many2one',
            relation='res.country.department', string='Department',
            readonly=True, store={
                'res.partner': (
                    lambda self, cr, uid, ids, c={}:
                    ids, ['zip', 'country_id', 'state_id'], 10),
                'res.country.department': (
                    _get_partner_from_department, ['code', 'state_id'], 20),
                }),
        }
