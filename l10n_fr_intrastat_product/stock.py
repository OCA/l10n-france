# -*- encoding: utf-8 -*-
##############################################################################
#
#    l10n FR Report intrastat product module for Odoo
#    Copyright (C) 2010-2015 Akretion (http://www.akretion.com)
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

from openerp import models, api, _
from openerp.exceptions import Warning as UserError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.multi
    def get_fr_department(self):
        # TODO : keep compat with other countries
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Missing partner on warehouse %s') % self.name)
        return self.partner_id.department_id


class StockLocation(models.Model):
    _inherit = 'stock.location'

    @api.multi
    def get_fr_department(self):
        '''I don't think it's a good idea to use the get_intrastat_region()
        of intrastat_product because it doesn't return the same object.
        That's why there is a small code duplication in this method'''
        self.ensure_one()
        locations = self.search(
            [('parent_left', '<=', self.parent_left),
             ('parent_right', '>=', self.parent_right)])
        warehouses = self.env['stock.warehouse'].search(
            [('lot_stock_id', 'in', [x.id for x in locations])])
        if warehouses:
            return warehouses[0].get_fr_department()
        return None
