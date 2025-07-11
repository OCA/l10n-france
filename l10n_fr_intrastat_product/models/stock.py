# Copyright 2010-2022 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    def _get_fr_department(self):
        self.ensure_one()
        return self.partner_id.country_department_id if self.partner_id else None


class StockLocation(models.Model):
    _inherit = "stock.location"

    def _get_fr_department(self):
        self.ensure_one()
        warehouse = self.env["stock.warehouse"].search(
            [("lot_stock_id", "parent_of", self.ids)], limit=1
        )
        if warehouse:
            return warehouse._get_fr_department()
        return None
