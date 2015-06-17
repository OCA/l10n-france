# -*- encoding: utf-8 -*-
##############################################################################
#
#    l10n FR Departments Delivery module for Odoo
#    Copyright (C) 2015 Akretion (http://www.akretion.com)
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


class DeliveryGrid(models.Model):
    _inherit = 'delivery.grid'

    department_ids = fields.Many2many(
        'res.country.department', string="Departments")


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    @api.multi
    def grid_get(self, contact_id):
        '''This is almost a copy-paste of the native grid_get() method
        from odoo/addons/delivery/delivery.py
        I didn't find a way to inherit this method via super() without too
        much computing overhead. So I decided to do an inherit without super()
        As this method is pretty small and pretty safe, it should not be a real
        problem.
        NOTE : when porting this method to new versions of Odoo, you should
        check the evolution of the code of the original method in
        odoo/addons/delivery/delivery.py
        This method is copyright Odoo S.A.
        '''
        contact = self.env['res.partner'].browse(contact_id)
        for carrier in self:
            for grid in carrier.grids_id:
                country_ids = grid.country_ids.ids
                state_ids = grid.state_ids.ids
                dpt_ids = grid.department_ids.ids
                if country_ids and contact.country_id.id not in country_ids:
                    continue
                if state_ids and contact.state_id.id not in state_ids:
                    continue
                if grid.zip_from and (contact.zip or '') < grid.zip_from:
                    continue
                if grid.zip_to and (contact.zip or '') > grid.zip_to:
                    continue
                if dpt_ids and contact.department_id.id not in dpt_ids:
                    continue
                return grid.id
        return False
