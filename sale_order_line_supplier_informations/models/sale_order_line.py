# Copyright 2024 Moka
# @author Horvat Damien <damien@moka.cloud>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"


    vendor_id = fields.Many2one(
        'res.partner',
        string="Fournisseur",
        domain="[('id', 'in', available_vendor_ids)]",
        help="Select a seller for this product",
    )

    available_vendor_ids = fields.Many2many(
        'res.partner', compute="_compute_available_vendor_ids", store=False
    )

    purchase_price = fields.Float(
        string="Purchase Price",
        compute="_compute_purchase_price", store=True
    )

    @api.depends('product_id', 'company_id', 'currency_id', 'product_uom', 'vendor_id')
    def _compute_purchase_price(self):
        for line in self:
            if not line.product_id:
                line.purchase_price = 0.0
                continue
            line = line.with_company(line.company_id)
            product_cost = line.product_id.standard_price
            if line.vendor_id:
                print("ICI changement cout achat")
                line.purchase_price = line.product_id.product_tmpl_id.seller_ids.filtered(lambda s: s.partner_id == line.vendor_id).price
            else:
                line.purchase_price = line._convert_price(product_cost, line.product_id.uom_id)
    
    @api.depends('product_id')
    def _compute_available_vendor_ids(self):
        for line in self:
            if line.product_id:
                vendor_ids = line.product_id.product_tmpl_id.mapped('seller_ids.partner_id').ids
                line.available_vendor_ids = vendor_ids
            else:
                line.available_vendor_ids = []