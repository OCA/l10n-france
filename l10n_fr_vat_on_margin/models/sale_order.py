from odoo import api, fields, models, Command, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.tools import float_compare
from odoo.tools.misc import get_lang


class SaleOrder(models.Model):
    _inherit = "sale.order"

    order_concerned_by_margin = fields.Boolean(
        string='Order Concerned by Margin',
        compute='_compute_order_concerned_by_margin',
    )


    @api.depends('order_line', 'order_line.product_id.vat_on_margin', 'order_line.product_id.categ_id.vat_on_margin')
    def _compute_order_concerned_by_margin(self):
        for order in self:
            order.order_concerned_by_margin = any(
                line.product_id.vat_on_margin or line.product_id.categ_id.vat_on_margin
                for line in order.order_line
            )
