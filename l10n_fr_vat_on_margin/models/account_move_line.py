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

    @api.depends('move_id')
    def _compute_balance(self):
        for line in self:
            if line.display_type in ('line_section', 'line_note'):
                line.balance = False
            elif not line.move_id.is_invoice(include_receipts=True):
                # Only act as a default value when none of balance/debit/credit is specified
                # balance is always the written field because of `_sanitize_vals`
                line.balance = -sum((line.move_id.line_ids - line).mapped('balance'))
            else:
                line.balance = 0

    @api.depends('balance', 'move_id.is_storno')
    def _compute_debit_credit(self):
        for line in self:
            if not line.is_storno:
                line.debit = line.balance if line.balance > 0.0 else 0.0
                line.credit = -line.balance if line.balance < 0.0 else 0.0
            else:
                line.debit = line.balance if line.balance < 0.0 else 0.0
                line.credit = -line.balance if line.balance > 0.0 else 0.0

    @api.depends('debit', 'credit', 'amount_currency', 'account_id', 'currency_id', 'company_id',
                 'matched_debit_ids', 'matched_credit_ids')
    def _compute_amount_residual(self):
        """ Computes the residual amount of a move line from a reconcilable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconcilable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        need_residual_lines = self.filtered(
            lambda x: x.account_id.reconcile or x.account_id.account_type in ('asset_cash', 'liability_credit_card'))
        # Run the residual amount computation on all lines stored in the db. By
        # using _origin, new records (with a NewId) are excluded and the
        # computation works automagically for virtual onchange records as well.
        stored_lines = need_residual_lines._origin

        if stored_lines:
            self.env['account.partial.reconcile'].flush_model()
            self.env['res.currency'].flush_model(['decimal_places'])

            aml_ids = tuple(stored_lines.ids)
            self._cr.execute('''
                             SELECT part.debit_move_id                                          AS line_id,
                                    'debit'                                                     AS flag,
                                    COALESCE(SUM(part.amount), 0.0)                             AS amount,
                                    ROUND(SUM(part.debit_amount_currency), curr.decimal_places) AS amount_currency
                             FROM account_partial_reconcile part
                                      JOIN res_currency curr ON curr.id = part.debit_currency_id
                             WHERE part.debit_move_id IN %s
                             GROUP BY part.debit_move_id, curr.decimal_places
                             UNION ALL
                             SELECT part.credit_move_id                                          AS line_id,
                                    'credit'                                                     AS flag,
                                    COALESCE(SUM(part.amount), 0.0)                              AS amount,
                                    ROUND(SUM(part.credit_amount_currency), curr.decimal_places) AS amount_currency
                             FROM account_partial_reconcile part
                                      JOIN res_currency curr ON curr.id = part.credit_currency_id
                             WHERE part.credit_move_id IN %s
                             GROUP BY part.credit_move_id, curr.decimal_places
                             ''', [aml_ids, aml_ids])
            amounts_map = {
                (line_id, flag): (amount, amount_currency)
                for line_id, flag, amount, amount_currency in self.env.cr.fetchall()
            }
        else:
            amounts_map = {}

        # Lines that can't be reconciled with anything since the account doesn't allow that.
        for line in self - need_residual_lines:
            line.amount_residual = 0.0
            line.amount_residual_currency = 0.0
            line.reconciled = False

        for line in need_residual_lines:
            # Since this part could be call on 'new' records, 'company_currency_id'/'currency_id' could be not set.
            comp_curr = line.company_currency_id or self.env.company.currency_id
            foreign_curr = line.currency_id or comp_curr
            # Retrieve the amounts in both foreign/company currencies. If the record is 'new', the amounts_map is empty.
            debit_amount, debit_amount_currency = amounts_map.get((line._origin.id, 'debit'), (0.0, 0.0))
            credit_amount, credit_amount_currency = amounts_map.get((line._origin.id, 'credit'), (0.0, 0.0))

            # Subtract the values from the account.partial.reconcile to compute the residual amounts.
            line.amount_residual = comp_curr.round(line.balance - debit_amount + credit_amount)
            line.amount_residual_currency = foreign_curr.round(
                line.amount_currency - debit_amount_currency + credit_amount_currency)
            line.reconciled = (
                comp_curr.is_zero(line.amount_residual)
                and foreign_curr.is_zero(line.amount_residual_currency)
            )

    @api.depends("vendor_id")
    def _compute_vendor_price(self):
        for rec in self:
            if rec.vendor_id:
                rec.vendor_price = rec.product_id.product_tmpl_id.seller_ids.filtered(
                    lambda s: s.partner_id == rec.vendor_id).price

    @api.depends('product_id')
    def _compute_available_vendor_ids(self):
        for line in self:
            if line.product_id:
                vendor_ids = line.product_id.product_tmpl_id.mapped('seller_ids.partner_id').ids
                line.available_vendor_ids = vendor_ids
            else:
                line.available_vendor_ids = []

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.
        :return: A python dictionary.
        """
        self.ensure_one()
        is_invoice = self.move_id.is_invoice(include_receipts=True)
        sign = -1 if self.move_id.is_inbound(include_receipts=True) else 1
        price_unit = self.price_unit if is_invoice else self.amount_currency
        price_unit_margin = 0.0
        if self.line_concerned_by_margin:
            price_unit = (self.price_unit - self.vendor_price)
            price_unit_margin = self.margin / self.quantity
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.partner_id,
            currency=self.currency_id,
            product=self.product_id,
            taxes=self.tax_ids,
            price_unit=price_unit,
            price_unit_margin=self.margin,
            quantity=self.quantity if is_invoice else 1.0,
            discount=self.discount if is_invoice else 0.0,
            account=self.account_id,
            analytic_distribution=self.analytic_distribution,
            price_subtotal=sign * self.amount_currency,
            is_refund=self.is_refund,
            rate=(abs(self.amount_currency) / abs(self.balance)) if self.balance else 1.0
        )

    @api.depends('product_id', 'price_unit', 'margin', 'quantity', 'vendor_price', 'tax_id')
    def _compute_margin_tax(self):
        for line in self:
            if line.line_concerned_by_margin:
                margin = (line.price_unit - line.vendor_price) * line.quantity
                if margin > 0:
                    for tax in line.tax_ids:
                        if tax.amount_type == 'percent':
                            tax_amount = margin * (tax.amount / 100)
                            line.tax_base_amount = margin
                            line.tax_amount = tax_amount
                        else:
                            line.tax_base_amount = line.price_subtotal
                            line.tax_amount = line.price_subtotal * (tax.amount / 100)
                else:
                    line.tax_base_amount = line.price_subtotal
                    line.tax_amount = 0.0
            else:
                line.tax_base_amount = line.price_subtotal
                line.tax_amount = line.price_subtotal * (line.tax_ids.amount / 100)

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
                    is_tva_on_margin_move=True,
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
            rate = line.amount_currency / line.balance if line.balance else 1
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
