from odoo import models, fields, api
from odoo.tools import frozendict, formatLang, format_date, float_compare, Query

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    vendor_id = fields.Many2one(
        'res.partner',
        string="Supplier",
        domain="[('id', 'in', available_vendor_ids)]",
        help="Select a seller for this product",
    )

    available_vendor_ids = fields.Many2many(
        'res.partner', compute="_compute_available_vendor_ids", store=False
    )

    vendor_price = fields.Float(
        string="Supplier Price",
        help="Price of the product for the supplier",
        domain="[('id', 'in', available_vendor_ids)]",
        compute="_compute_vendor_price", store=True
    )

    purchase_price = fields.Float(
        string='Purchase Price',
        digits="Purchase Price",
        default=0.0,
    )

    margin = fields.Float(
        string='Margin',
        compute="_compute_margin_untaxed",
        store=True, readonly=True,
        help="Gross margin (Sales - Purchase)"
    )

    @api.depends('purchase_price', 'price_unit', 'quantity', 'discount', 'tax_ids')
    def _compute_margin_untaxed(self):
        for line in self:
            # 1. Calcul du prix unitaire après remise
            price_unit_discounted = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

            # 2. Calcul du montant HT
            price_subtotal = price_unit_discounted * line.quantity

            # 3. Calcul des taxes pour obtenir le TTC
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    price_unit_discounted,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                )
                price_total_calculated = taxes_res['total_included']
            else:
                price_total_calculated = price_subtotal

            # 4. Calcul du coût d'achat total
            purchase_total = line.purchase_price * line.quantity

            # 5. Marge brute TTC
            margin_brut_ttc = price_total_calculated - purchase_total

            line.margin = margin_brut_ttc

    line_concerned_by_margin = fields.Boolean(
        string='Line Concerned by Margin',
        compute='_compute_line_concerned_by_margin',
        store=True,
    )

    @api.depends('tax_ids')
    def _compute_line_concerned_by_margin(self):
        for line in self:
            line.line_concerned_by_margin = any(
                tax.vat_on_margin for tax in line.tax_ids
            )

    @api.depends("vendor_id")
    def _compute_vendor_price(self):
        for rec in self:
            # Assign on every branch: without the else the price stayed at
            # its previous value after the supplier was removed.
            rec.vendor_price = rec.product_id.product_tmpl_id.seller_ids.filtered(
                lambda s: s.partner_id == rec.vendor_id
            ).price if rec.vendor_id else 0.0

    @api.depends('product_id')
    def _compute_available_vendor_ids(self):
        for line in self:
            if line.product_id:
                vendor_ids = line.product_id.product_tmpl_id.mapped('seller_ids.partner_id').ids
                line.available_vendor_ids = vendor_ids
            else:
                line.available_vendor_ids = []

    def _convert_to_tax_base_line_dict(self):
        """Add the margin to the dict the tax engine consumes.

        The margin travels through this key alone. It used to be subtracted
        from price_unit as well, counting it twice: the totals block printed
        10.00 where the journal entry posted 120.00.
        """
        res = super()._convert_to_tax_base_line_dict()
        if self.line_concerned_by_margin:
            res['price_unit_margin'] = self.margin
        return res

    @api.depends('quantity', 'discount', 'price_unit', 'margin', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        for line in self:
            if line.display_type != 'product':
                line.price_total = line.price_subtotal = False
            # Compute 'price_subtotal'.
            line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line_discount_price_unit
            # Compute 'price_total  '.
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                    price_unit_margin=line.margin
                )
                line.price_subtotal = taxes_res['total_excluded']
                line.price_total = taxes_res['total_included']
            else:
                line.price_total = line.price_subtotal = subtotal

    @api.depends('tax_ids', 'currency_id', 'partner_id', 'analytic_distribution', 'balance', 'partner_id',
                 'move_id.partner_id', 'price_unit', 'margin', 'quantity')
    def _compute_all_tax(self):
        for line in self:
            sign = line.move_id.direction_sign
            if line.display_type == 'tax':
                line.compute_all_tax = {}
                line.compute_all_tax_dirty = False
                continue
            if line.display_type == 'product' and line.move_id.is_invoice(True):
                amount_currency = sign * line.price_unit * (1 - line.discount / 100)
                handle_price_include = True
                quantity = line.quantity
            else:
                amount_currency = line.amount_currency
                handle_price_include = False
                quantity = 1
            compute_all_currency = line.tax_ids.compute_all(
                amount_currency,
                currency=line.currency_id,
                quantity=quantity,
                product=line.product_id,
                partner=line.move_id.partner_id or line.partner_id,
                is_refund=line.is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=line.move_id.always_tax_exigible,
                fixed_multiplicator=sign,
                price_unit_margin=line.margin,
            )
            rate = line.amount_currency / line.balance if line.balance else line.currency_rate
            line.compute_all_tax_dirty = True
            line.compute_all_tax = {
                frozendict({
                    'tax_repartition_line_id': tax['tax_repartition_line_id'],
                    'group_tax_id': tax['group'] and tax['group'].id or False,
                    'account_id': tax['account_id'] or line.account_id.id,
                    'currency_id': line.currency_id.id,
                    'analytic_distribution': ((tax['analytic'] or not tax[
                        'use_in_tax_closing']) and line.move_id.state == 'draft') and line.analytic_distribution,
                    'tax_ids': [(6, 0, tax['tax_ids'])],
                    'tax_tag_ids': [(6, 0, tax['tag_ids'])],
                    'partner_id': line.move_id.partner_id.id or line.partner_id.id,
                    'move_id': line.move_id.id,
                    'display_type': line.display_type,
                }): {
                    'name': tax['name'] + (' ' + _('(Discount)') if line.display_type == 'epd' else ''),
                    'balance': tax['amount'] / rate,
                    'amount_currency': tax['amount'],
                    'tax_base_amount': tax['base'] / rate * (-1 if line.tax_tag_invert else 1),
                }
                for tax in compute_all_currency['taxes']
                if tax['amount']
            }
            if not line.tax_repartition_line_id:
                line.compute_all_tax[frozendict({'id': line.id})] = {
                    'tax_tag_ids': [(6, 0, compute_all_currency['base_tags'])],
                }
