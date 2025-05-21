# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date, formatLang

from collections import defaultdict
from odoo.tools import groupby, frozendict
import json

class SaleOrderFiscalPositionWizard(models.TransientModel):
    _name = "sale.order.fiscal.position.wizard"
    _description = "Sale Order Fiscal Position Wizard"

    def change_fiscal_position(self):
        """
        Change fiscal position to VAT on margin.
        """
        self.ensure_one()

        # Get the sale order
        sale_order = self.env['sale.order'].browse(self._context.get('default_sale_order_id'))

        # Get the VAT on margin fiscal position
        vat_margin_fiscal_position = self.env['account.fiscal.position'].browse(self._context.get('default_vat_margin_fiscal_position_id'))

        # Change the fiscal position
        sale_order.fiscal_position_id = vat_margin_fiscal_position

        return {
            'type': 'ir.actions.act_window_close',
        }

