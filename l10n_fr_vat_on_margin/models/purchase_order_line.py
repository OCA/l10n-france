from odoo import api, fields, models, Command, _


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    margin_amount = fields.Float(
        string='Margin Amount',
    )

    line_concerned_by_margin = fields.Boolean(
        string='Line Concerned by Margin',
        compute='_compute_line_concerned_by_margin',
        store=True,
    )

    @api.depends('taxes_id')
    def _compute_line_concerned_by_margin(self):
        for line in self:
            if line.taxes_id.filtered(lambda tax: tax.vat_on_margin):
                line.line_concerned_by_margin = True



    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        print("=== _convert_to_tax_base_line_dict ===", self, self.margin_amount)
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.taxes_id,
            price_unit=self.price_unit,
            price_unit_margin=self.margin_amount,
            quantity=self.product_qty,
            price_subtotal=self.price_subtotal,
        )

    def _prepare_account_move_line(self, move=False):
        print("=== _prepare_account_move_line ===", self, self.margin_amount)
        self.ensure_one()
        aml_currency = move and move.currency_id or self.currency_id
        date = move and move.date or fields.Date.today()
        price_unit = self.currency_id._convert(self.price_unit, aml_currency, self.company_id, date, round=False)
        res = {
            'display_type': self.display_type or 'product',
            'name': '%s: %s' % (self.order_id.name, self.name),
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'price_unit': price_unit,
            'margin_amount': self.margin_amount,
            'tax_ids': [(6, 0, self.taxes_id.ids)],
            'purchase_line_id': self.id,
        }
        if self.analytic_distribution and not self.display_type:
            res['analytic_distribution'] = self.analytic_distribution
        return res