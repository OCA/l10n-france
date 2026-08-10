from odoo import api, fields, models, Command, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.tools import float_compare
from odoo.tools.misc import get_lang


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    margin_amount_untaxed = fields.Float(
        string='Margin Amount Before Tax',
        compute='_compute_margin_untaxed',
        store=True,
        help='Margin amount before tax.',
    )

    line_concerned_by_margin = fields.Boolean(
        string='Line Concerned by Margin',
        compute='_compute_line_concerned_by_margin',
        store=True,
    )

    @api.depends('tax_id')
    def _compute_line_concerned_by_margin(self):
        for line in self:
            # Assign on every branch: without the False case the flag stayed True
            # after the margin tax was replaced by a regular one.
            line.line_concerned_by_margin = any(
                tax.vat_on_margin for tax in line.tax_id
            )

    @api.onchange('product_id')
    def _onchange_product_id_warning_margin(self):
        if self.product_id.vat_on_margin or self.product_id.categ_id.vat_on_margin:
            if not self.order_id.fiscal_position_id.vat_on_margin:
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _(
                            'This order is concerned by VAT on margin. You should select the VAT on margin fiscal position.')
                    }
                }

    @api.depends('purchase_price', 'price_unit', 'product_uom_qty', 'discount', 'tax_id')
    def _compute_margin_untaxed(self):
        for line in self:
            # 1. Calcul du prix unitaire après remise
            price_unit_discounted = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

            # 2. Calcul du montant HT
            price_subtotal = price_unit_discounted * line.product_uom_qty

            # 3. Calcul des taxes pour obtenir le TTC
            if line.tax_id:
                # Compute_all retourne les taxes calculées
                taxes = line.tax_id.compute_all(
                    price_unit_discounted,
                    line.order_id.currency_id,
                    line.product_uom_qty,
                    product=line.product_id,
                    partner=line.order_id.partner_id
                )
                price_total_calculated = taxes['total_included']
            else:
                price_total_calculated = price_subtotal

            # 4. Calcul du coût d'achat total
            purchase_total = line.purchase_price * line.product_uom_qty

            # 5. Marge brute TTC
            margin_brut_ttc = price_total_calculated - purchase_total

            line.margin_amount_untaxed = margin_brut_ttc

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        price_unit_margin = 0.0
        if self.line_concerned_by_margin:
            price_unit_margin = self.margin_amount_untaxed
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit,
            price_unit_margin=price_unit_margin,
            quantity=self.product_uom_qty,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
        )

    @api.depends('state', 'price_reduce', 'product_id', 'untaxed_amount_invoiced', 'qty_delivered', 'product_uom_qty')
    def _compute_untaxed_amount_to_invoice(self):
        """ Total of remaining amount to invoice on the sale order line (taxes excl.) as
                total_sol - amount already invoiced
            where Total_sol depends on the invoice policy of the product.

            Note: Draft invoice are ignored on purpose, the 'to invoice' amount should
            come only from the SO lines.
        """
        for line in self:
            amount_to_invoice = 0.0
            if line.state in ['sale', 'done']:
                # Note: do not use price_subtotal field as it returns zero when the ordered quantity is
                # zero. It causes problem for expense line (e.i.: ordered qty = 0, deli qty = 4,
                # price_unit = 20 ; subtotal is zero), but when you can invoice the line, you see an
                # amount and not zero. Since we compute untaxed amount, we can use directly the price
                # reduce (to include discount) without using `compute_all()` method on taxes.
                price_subtotal = 0.0
                uom_qty_to_consider = line.qty_delivered if line.product_id.invoice_policy == 'delivery' else line.product_uom_qty
                price_reduce = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                price_subtotal = price_reduce * uom_qty_to_consider
                if len(line.tax_id.filtered(lambda tax: tax.price_include)) > 0:
                    # As included taxes are not excluded from the computed subtotal, `compute_all()` method
                    # has to be called to retrieve the subtotal without them.
                    # `price_reduce_taxexcl` cannot be used as it is computed from `price_subtotal` field. (see upper Note)

                    price_subtotal = line.tax_id.compute_all(
                        price_reduce,
                        currency=line.currency_id,
                        quantity=uom_qty_to_consider,
                        product=line.product_id,
                        partner=line.order_id.partner_shipping_id,
                        price_unit_margin=line.margin_amount_untaxed)['total_excluded']
                inv_lines = line._get_invoice_lines()
                if any(inv_lines.mapped(lambda l: l.discount != line.discount)):
                    # In case of re-invoicing with different discount we try to calculate manually the
                    # remaining amount to invoice
                    amount = 0
                    for l in inv_lines:
                        if len(l.tax_ids.filtered(lambda tax: tax.price_include)) > 0:
                            amount += l.tax_ids.compute_all(
                                l.currency_id._convert(l.price_unit, line.currency_id, line.company_id,
                                                       l.date or fields.Date.today(), round=False) * l.quantity)[
                                'total_excluded']
                        else:
                            amount += l.currency_id._convert(l.price_unit, line.currency_id, line.company_id,
                                                             l.date or fields.Date.today(), round=False) * l.quantity

                    amount_to_invoice = max(price_subtotal - amount, 0)
                else:
                    amount_to_invoice = price_subtotal - line.untaxed_amount_invoiced

            line.untaxed_amount_to_invoice = amount_to_invoice

    def _prepare_invoice_line(self, **optional_values):
        """Prepare the values to create the new invoice line for a sales order line.
        :param optional_values: any parameter that should be added to the returned invoice line
        :rtype: dict
        """
        self.ensure_one()
        res = {
            'display_type': self.display_type or 'product',
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'discount': self.discount,
            'price_unit': self.price_unit,
            'purchase_price': self.purchase_price,
            'tax_ids': [Command.set(self.tax_id.ids)],
            'sale_line_ids': [Command.link(self.id)],
            'is_downpayment': self.is_downpayment,
        }
        analytic_account_id = self.order_id.analytic_account_id.id
        if self.analytic_distribution and not self.display_type:
            res['analytic_distribution'] = self.analytic_distribution
        if analytic_account_id and not self.display_type:
            analytic_account_id = str(analytic_account_id)
            if 'analytic_distribution' in res:
                res['analytic_distribution'][analytic_account_id] = res['analytic_distribution'].get(
                    analytic_account_id, 0) + 100
            else:
                res['analytic_distribution'] = {analytic_account_id: 100}
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res
