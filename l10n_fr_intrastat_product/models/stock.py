# Copyright 2010-2019 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, _
from odoo.exceptions import UserError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def get_fr_department(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Missing partner on warehouse %s') % self.name)
        return self.partner_id.department_id


class StockLocation(models.Model):
    _inherit = 'stock.location'

    def get_fr_department(self):
        '''I don't think it's a good idea to use the get_intrastat_region()
        of intrastat_product because it doesn't return the same object.
        That's why there is a small code duplication in this method'''
        self.ensure_one()
        locations = self.search(
            [('id', 'parent_of', self.id)])
        warehouses = self.env['stock.warehouse'].search(
            [('lot_stock_id', 'in', locations.ids)])
        if warehouses:
            return warehouses[0].get_fr_department()
        return None
