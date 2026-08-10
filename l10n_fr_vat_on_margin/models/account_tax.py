from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import frozendict
from odoo.tools.safe_eval import safe_eval

from collections import defaultdict
import math
import re


class AccountTax(models.Model):
    _inherit = 'account.tax'

    tax_calculation_method = fields.Selection(
        [('margin', 'Margin'), ('normal', 'Normal')],
        string="Tax Calculation Method",
        help="Method used for calculating tax",
        default='normal',
        required=False
    )

    amount_type = fields.Selection(
        selection_add=[('margin_percentage', 'Margin Percentage')],
        ondelete={'margin_percentage': 'cascade'}
    )

    vat_on_margin = fields.Boolean(
        string="VAT on Margin",
        help="Check this box if the tax is a VAT on margin.",
        default=False
    )

    # @api.model
    # def compute_margin_tax(self, product, price_unit, quantity, vendor_price):
    #     """
    #     Calculer la TVA sur la marge : (prix de vente - coût fournisseur) x taux.
    #     Cette méthode est applicable uniquement si 'tax_calculation_method' est 'margin'.
    #     """
    #     if not product or not self.tax_calculation_method == 'margin':
    #         return 0.0
    #
    #     # Calcul de la marge (prix unitaire - coût fournisseur)
    #     margin = price_unit - vendor_price
    #
    #     if margin > 0:
    #         tax_amount = margin * (self.amount / 100) * quantity
    #         return tax_amount
    #     return 0.0
    #
    def _convert_to_tax_base_line_dict(
            self, base_line,
            partner=None, currency=None, product=None, taxes=None, price_unit=None, price_unit_margin=None,
            quantity=None,
            discount=None, account=None, analytic_distribution=None, price_subtotal=None,
            is_refund=False, rate=None,
            handle_price_include=True,
            extra_context=None,
    ):
        taxes = taxes or self.env['account.tax']
        return {
            'record': base_line,
            'partner': partner or self.env['res.partner'],
            'currency': currency or self.env['res.currency'],
            'product': product or self.env['product.product'],
            'taxes': taxes,
            'price_unit': price_unit or 0.0,
            # Keep the raw margin, negative values included: the tax computation must
            # be able to tell "no margin scheme" from "margin scheme, nothing to tax".
            'price_unit_margin': (price_unit_margin or 0.0) if any(taxes.mapped('vat_on_margin')) else 0.0,
            'quantity': quantity or 0.0,
            'discount': discount or 0.0,
            'account': account or self.env['account.account'],
            'analytic_distribution': analytic_distribution,
            'price_subtotal': price_subtotal or 0.0,
            'is_refund': is_refund,
            'rate': rate or 1.0,
            'handle_price_include': handle_price_include,
            'extra_context': extra_context or {},
        }


    @api.model
    def _compute_taxes_for_single_line(self, base_line, handle_price_include=True, include_caba_tags=False,
                                       early_pay_discount_computation=None, early_pay_discount_percentage=None):
        orig_price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
        # Forward the margin as-is; clamping it to zero here would make a negative
        # margin indistinguishable from a line that has no margin scheme at all.
        price_unit_margin = base_line['price_unit_margin']
        price_unit_after_discount = orig_price_unit_after_discount
        taxes = base_line['taxes']._origin
        vat_on_margin = any(taxes.mapped('vat_on_margin'))
        currency = base_line['currency'] or self.env.company.currency_id
        rate = base_line['rate']

        if early_pay_discount_computation in ('included', 'excluded'):
            remaining_part_to_consider = (100 - early_pay_discount_percentage) / 100.0
            price_unit_after_discount = remaining_part_to_consider * price_unit_after_discount

        if taxes:
            taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                price_unit_after_discount,
                currency=currency,
                quantity=base_line['quantity'],
                product=base_line['product'],
                partner=base_line['partner'],
                is_refund=base_line['is_refund'],
                handle_price_include=base_line['handle_price_include'],
                include_caba_tags=include_caba_tags,
                price_unit_margin=price_unit_margin if vat_on_margin else 0.0,
            )

            to_update_vals = {
                'tax_tag_ids': [Command.set(taxes_res['base_tags'])],
                'price_subtotal': taxes_res['total_excluded'],
                'price_total': taxes_res['total_included'],
            }

            if early_pay_discount_computation == 'excluded':
                new_taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                    orig_price_unit_after_discount,
                    currency=currency,
                    quantity=base_line['quantity'],
                    product=base_line['product'],
                    partner=base_line['partner'],
                    is_refund=base_line['is_refund'],
                    handle_price_include=base_line['handle_price_include'],
                    include_caba_tags=include_caba_tags,
                    price_unit_margin=price_unit_margin if vat_on_margin else 0.0,
                )
                for tax_res, new_taxes_res in zip(taxes_res['taxes'], new_taxes_res['taxes']):
                    delta_tax = new_taxes_res['amount'] - tax_res['amount']
                    tax_res['amount'] += delta_tax
                    to_update_vals['price_total'] += delta_tax

            tax_values_list = []
            for tax_res in taxes_res['taxes']:
                tax_amount = tax_res['amount'] / rate
                if self.company_id.tax_calculation_rounding_method == 'round_per_line':
                    tax_amount = currency.round(tax_amount)
                tax_rep = self.env['account.tax.repartition.line'].browse(tax_res['tax_repartition_line_id'])
                tax_values_list.append({
                    **tax_res,
                    'tax_repartition_line': tax_rep,
                    'base_amount_currency': tax_res['base'],
                    'base_amount': currency.round(tax_res['base'] / rate),
                    'tax_amount_currency': tax_res['amount'],
                    'tax_amount': tax_amount,
                })

        else:
            price_subtotal = currency.round(price_unit_after_discount * base_line['quantity'])
            to_update_vals = {
                'tax_tag_ids': [Command.clear()],
                'price_subtotal': price_subtotal,
                'price_total': price_subtotal,
            }
            tax_values_list = []

        return to_update_vals, tax_values_list

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False,
                    handle_price_include=True, include_caba_tags=False, fixed_multiplicator=1, **kwargs):
        """Compute all information required to apply taxes (in self + their children in case of a tax group).
        We consider the sequence of the parent for group of taxes.
            Eg. considering letters as taxes and alphabetic order as sequence :
            [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]



        :param price_unit: The unit price of the line to compute taxes on.
        :param currency: The optional currency in which the price_unit is expressed.
        :param quantity: The optional quantity of the product to compute taxes on.
        :param product: The optional product to compute taxes on.
            Used to get the tags to apply on the lines.
        :param partner: The optional partner compute taxes on.
            Used to retrieve the lang to build strings and for potential extensions.
        :param is_refund: The optional boolean indicating if this is a refund.
        :param handle_price_include: Used when we need to ignore all tax included in price. If False, it means the
            amount passed to this method will be considered as the base of all computations.
        :param include_caba_tags: The optional boolean indicating if CABA tags need to be taken into account.
        :param fixed_multiplicator: The amount to multiply fixed amount taxes by.
        :return: {
            'total_excluded': 0.0,    # Total without taxes
            'total_included': 0.0,    # Total with taxes
            'total_void'    : 0.0,    # Total with those taxes, that don't have an account set
            'base_tags: : list<int>,  # Tags to apply on the base line
            'taxes': [{               # One dict for each tax in self and their children
                'id': int,
                'name': str,
                'amount': float,
                'base': float,
                'sequence': int,
                'account_id': int,
                'refund_account_id': int,
                'analytic': bool,
                'price_include': bool,
                'tax_exigibility': str,
                'tax_repartition_line_id': int,
                'group': recordset,
                'tag_ids': list<int>,
                'tax_ids': list<int>,
            }],
        } """
        if not self:
            company = self.env.company
        else:
            company = self[0].company_id

        # 1) Flatten the taxes.
        taxes, groups_map = self.flatten_taxes_hierarchy(create_map=True)

        # 2) Deal with the rounding methods
        if not currency:
            currency = company.currency_id

        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
        prec = currency.rounding

        # In some cases, it is necessary to force/prevent the rounding of the tax and the total
        # amounts. For example, in SO/PO line, we don't want to round the price unit at the
        # precision of the currency.
        # The context key 'round' allows to force the standard behavior.
        round_tax = False if company.tax_calculation_rounding_method == 'round_globally' else True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])

        if not round_tax:
            prec *= 1e-5

        # 3) Iterate the taxes in the reversed sequence order to retrieve the initial base of the computation.
        #     tax  |  base  |  amount  |
        # /\ ----------------------------
        # || tax_1 |  XXXX  |          | <- we are looking for that, it's the total_excluded
        # || tax_2 |   ..   |          |
        # || tax_3 |   ..   |          |
        # ||  ...  |   ..   |    ..    |
        #    ----------------------------
        def recompute_base(base_amount, incl_tax_amounts):
            """ Recompute the new base amount based on included fixed/percent amounts and the current base amount. """
            fixed_amount = incl_tax_amounts['fixed_amount']
            division_amount = sum(tax_factor for _i, tax_factor in incl_tax_amounts['division_taxes'])
            percent_amount = sum(tax_amount * sum_repartition_factor for _i, tax_amount, sum_repartition_factor in
                                 incl_tax_amounts['percent_taxes'])

            if company.country_code == 'IN':
                # For the indian case, when facing two percent price-included taxes having the same percentage,
                # both need to produce the same tax amounts. To do that, the tax amount of those taxes are computed
                # directly during the first traveling in reversed order.
                total_tax_amount = 0.0
                for i, tax_amount, sum_repartition_factor in incl_tax_amounts['percent_taxes']:
                    gross_tax_amount = float_round(base * tax_amount / (100 + percent_amount), precision_rounding=prec)
                    factored_tax_amount = float_round(gross_tax_amount * sum_repartition_factor,
                                                      precision_rounding=prec)
                    total_tax_amount += factored_tax_amount
                    cached_tax_amounts[i] = gross_tax_amount
                    fixed_amount += factored_tax_amount
                for i, _tax_amount, _sum_repartition_factor in incl_tax_amounts['percent_taxes']:
                    cached_base_amounts[i] = base - total_tax_amount
                percent_amount = 0.0

            incl_tax_amounts.update({
                'percent_taxes': [],
                'division_taxes': [],
                'fixed_amount': 0.0,
            })

            standard_base = (base_amount - fixed_amount) / (1.0 + percent_amount / 100.0) \
                * (100 - division_amount) / 100

            # 'self' holds every tax of the line, not a single one. Testing the flag
            # on the recordset itself raises "Expected singleton" as soon as a line
            # carries two taxes (e.g. margin VAT + eco-contribution).
            if not any(self.mapped('vat_on_margin')):
                return standard_base

            price_unit_margin = kwargs.get('price_unit_margin') or 0.0
            if price_unit_margin > 0.0:
                # Only the margin bears the VAT, the rest of the price stays untaxed.
                return base_amount - price_unit_margin + (
                    (price_unit_margin - fixed_amount) / (1.0 + percent_amount / 100.0)
                    * (100 - division_amount) / 100
                )

            # Nil or negative margin: no VAT is due under the margin scheme, so the
            # whole price is the untaxed base. Falling back to the standard formula
            # would tax the full price instead of nothing.
            return base_amount

        # The first/last base must absolutely be rounded to work in round globally.
        # Indeed, the sum of all taxes ('taxes' key in the result dictionary) must be strictly equals to
        # 'price_included' - 'price_excluded' whatever the rounding method.
        #
        # Example using the global rounding without any decimals:
        # Suppose two invoice lines: 27000 and 10920, both having a 19% price included tax.
        #
        #                   Line 1                      Line 2
        # -----------------------------------------------------------------------
        # total_included:   27000                       10920
        # tax:              27000 / 1.19 = 4310.924     10920 / 1.19 = 1743.529
        # total_excluded:   22689.076                   9176.471
        #
        # If the rounding of the total_excluded isn't made at the end, it could lead to some rounding issues
        # when summing the tax amounts, e.g. on invoices.
        # In that case:
        #  - amount_untaxed will be 22689 + 9176 = 31865
        #  - amount_tax will be 4310.924 + 1743.529 = 6054.453 ~ 6054
        #  - amount_total will be 31865 + 6054 = 37919 != 37920 = 27000 + 10920
        #
        # By performing a rounding at the end to compute the price_excluded amount, the amount_tax will be strictly
        # equals to 'price_included' - 'price_excluded' after rounding and then:
        #   Line 1: sum(taxes) = 27000 - 22689 = 4311
        #   Line 2: sum(taxes) = 10920 - 2176 = 8744
        #   amount_tax = 4311 + 8744 = 13055
        #   amount_total = 31865 + 13055 = 37920
        base = price_unit * quantity
        if self._context.get('round_base', True):
            base = currency.round(base)

        # For the computation of move lines, we could have a negative base value.
        # In this case, compute all with positive values and negate them at the end.
        sign = 1
        if currency.is_zero(base):
            sign = -1 if fixed_multiplicator < 0 else 1
        elif base < 0:
            sign = -1
            base = -base

        # Store the totals to reach when using price_include taxes (only the last price included in row)
        total_included_checkpoints = {}
        i = len(taxes) - 1
        store_included_tax_total = True
        # Keep track of the accumulated included fixed/percent amount.
        incl_tax_amounts = {
            'percent_taxes': [],
            'division_taxes': [],
            'fixed_amount': 0.0,
        }
        # Store the tax amounts we compute while searching for the total_excluded
        cached_base_amounts = {}
        cached_tax_amounts = {}
        is_base_affected = True
        if handle_price_include:
            for tax in reversed(taxes):
                tax_repartition_lines = (
                        is_refund
                        and tax.refund_repartition_line_ids
                        or tax.invoice_repartition_line_ids
                ).filtered(lambda x: x.repartition_type == "tax")
                sum_repartition_factor = sum(tax_repartition_lines.mapped("factor"))

                if tax.include_base_amount and is_base_affected:
                    base = recompute_base(base, incl_tax_amounts)
                    store_included_tax_total = True
                if self._context.get('force_price_include', tax.price_include):
                    if tax.amount_type == 'percent' or tax.amount_type == 'margin_percentage':
                        incl_tax_amounts['percent_taxes'].append((i, tax.amount, sum_repartition_factor))
                    elif tax.amount_type == 'division':
                        incl_tax_amounts['division_taxes'].append((i, tax.amount * sum_repartition_factor))
                    elif tax.amount_type == 'fixed':
                        incl_tax_amounts['fixed_amount'] = abs(quantity) * tax.amount * sum_repartition_factor * abs(
                            fixed_multiplicator)
                    else:
                        # tax.amount_type == other (python)
                        tax_amount = tax._compute_amount(base, sign * price_unit, quantity, product, partner,
                                                         fixed_multiplicator)
                        tax_amount = float_round(tax_amount, precision_rounding=prec)
                        incl_tax_amounts['fixed_amount'] += tax_amount
                        # Avoid unecessary re-computation
                        cached_tax_amounts[i] = tax_amount
                    # In case of a zero tax, do not store the base amount since the tax amount will
                    # be zero anyway. Group and Python taxes have an amount of zero, so do not take
                    # them into account.
                    if store_included_tax_total and (
                            tax.amount or tax.amount_type not in ("percent", "division", "fixed")
                    ):
                        total_included_checkpoints[i] = base
                        store_included_tax_total = False
                i -= 1
                is_base_affected = tax.is_base_affected

        total_excluded = recompute_base(base, incl_tax_amounts)
        if self._context.get('round_base', True):
            total_excluded = currency.round(total_excluded)

        # Under the margin scheme the taxable base is the margin excluding tax,
        # not the net price. It is what the tax line stores as tax_base_amount
        # and therefore what the VAT return adds up: reporting the net price
        # yields a base and a tax amount that do not match the rate.
        # Derived from total_excluded rather than redoing the rate arithmetic,
        # since recompute_base() returned base - margin_incl + margin_excl.
        margin_tax_base = None
        if any(self.mapped('vat_on_margin')):
            margin_incl = kwargs.get('price_unit_margin') or 0.0
            margin_tax_base = (
                total_excluded - base + margin_incl if margin_incl > 0.0 else 0.0
            )

        # 4) Iterate the taxes in the sequence order to compute missing tax amounts.
        # Start the computation of accumulated amounts at the total_excluded value.
        base = total_included = total_void = total_excluded

        # Flag indicating the checkpoint used in price_include to avoid rounding issue must be skipped since the base
        # amount has changed because we are currently mixing price-included and price-excluded include_base_amount
        # taxes.
        skip_checkpoint = False

        # Get product tags, account.account.tag objects that need to be injected in all
        # the tax_tag_ids of all the move lines created by the compute all for this product.
        product_tag_ids = product.sudo().account_tag_ids.ids if product else []

        taxes_vals = []
        i = 0
        cumulated_tax_included_amount = 0
        for tax in taxes:
            price_include = self._context.get('force_price_include', tax.price_include)

            if price_include and i in cached_base_amounts:
                tax_base_amount = cached_base_amounts[i]
            elif price_include or tax.is_base_affected:
                tax_base_amount = base
            else:
                tax_base_amount = total_excluded

            tax_repartition_lines = (
                        is_refund and tax.refund_repartition_line_ids or tax.invoice_repartition_line_ids).filtered(
                lambda x: x.repartition_type == 'tax')
            sum_repartition_factor = sum(tax_repartition_lines.mapped('factor'))

            # compute the tax_amount
            if price_include and i in cached_tax_amounts:
                tax_amount = cached_tax_amounts[i]
            elif not skip_checkpoint and price_include and total_included_checkpoints.get(
                    i) is not None and sum_repartition_factor != 0:
                # We know the total to reach for that tax, so we make a substraction to avoid any rounding issues
                tax_amount = total_included_checkpoints[i] - (base + cumulated_tax_included_amount)
                cumulated_tax_included_amount = 0
            else:
                tax_amount = tax.with_context(force_price_include=False)._compute_amount(
                    tax_base_amount, sign * price_unit, quantity, product, partner, fixed_multiplicator)

            # Round the tax_amount multiplied by the computed repartition lines factor.
            tax_amount = float_round(tax_amount, precision_rounding=prec)
            factorized_tax_amount = float_round(tax_amount * sum_repartition_factor, precision_rounding=prec)

            if price_include and total_included_checkpoints.get(i) is None:
                cumulated_tax_included_amount += factorized_tax_amount

            # If the tax affects the base of subsequent taxes, its tax move lines must
            # receive the base tags and tag_ids of these taxes, so that the tax report computes
            # the right total
            subsequent_taxes = self.env['account.tax']
            subsequent_tags = self.env['account.account.tag']
            if tax.include_base_amount:
                subsequent_taxes = taxes[i + 1:].filtered('is_base_affected')

                taxes_for_subsequent_tags = subsequent_taxes

                if not include_caba_tags:
                    taxes_for_subsequent_tags = subsequent_taxes.filtered(lambda x: x.tax_exigibility != 'on_payment')

                subsequent_tags = taxes_for_subsequent_tags.get_tax_tags(is_refund, 'base')

            # Compute the tax line amounts by multiplying each factor with the tax amount.
            # Then, spread the tax rounding to ensure the consistency of each line independently with the factorized
            # amount. E.g:
            #
            # Suppose a tax having 4 x 50% repartition line applied on a tax amount of 0.03 with 2 decimal places.
            # The factorized_tax_amount will be 0.06 (200% x 0.03). However, each line taken independently will compute
            # 50% * 0.03 = 0.01 with rounding. It means there is 0.06 - 0.04 = 0.02 as total_rounding_error to dispatch
            # in lines as 2 x 0.01.
            repartition_line_amounts = [float_round(tax_amount * line.factor, precision_rounding=prec) for line in
                                        tax_repartition_lines]
            total_rounding_error = float_round(factorized_tax_amount - sum(repartition_line_amounts),
                                               precision_rounding=prec)
            nber_rounding_steps = int(abs(total_rounding_error / currency.rounding))
            rounding_error = float_round(nber_rounding_steps and total_rounding_error / nber_rounding_steps or 0.0,
                                         precision_rounding=prec)

            for repartition_line, line_amount in zip(tax_repartition_lines, repartition_line_amounts):

                if nber_rounding_steps:
                    line_amount += rounding_error
                    nber_rounding_steps -= 1

                if not include_caba_tags and tax.tax_exigibility == 'on_payment':
                    repartition_line_tags = self.env['account.account.tag']
                else:
                    repartition_line_tags = repartition_line.tag_ids

                # Only the margin tax reports the margin; a regular tax sharing
                # the same line keeps the ordinary base.
                reported_base = tax_base_amount
                if margin_tax_base is not None and tax.vat_on_margin:
                    reported_base = margin_tax_base

                taxes_vals.append({
                    'id': tax.id,
                    'name': partner and tax.with_context(lang=partner.lang).name or tax.name,
                    'amount': sign * line_amount,
                    'base': float_round(sign * reported_base, precision_rounding=prec),
                    'sequence': tax.sequence,
                    'account_id': repartition_line._get_aml_target_tax_account(
                        force_caba_exigibility=include_caba_tags).id,
                    'analytic': tax.analytic,
                    'use_in_tax_closing': repartition_line.use_in_tax_closing,
                    'price_include': price_include,
                    'tax_exigibility': tax.tax_exigibility,
                    'tax_repartition_line_id': repartition_line.id,
                    'group': groups_map.get(tax),
                    'tag_ids': (repartition_line_tags + subsequent_tags).ids + product_tag_ids,
                    'tax_ids': subsequent_taxes.ids,
                })

                if not repartition_line.account_id:
                    total_void += line_amount

            # Affect subsequent taxes
            if tax.include_base_amount:
                base += factorized_tax_amount
                if not price_include:
                    skip_checkpoint = True

            total_included += factorized_tax_amount
            i += 1

        base_taxes_for_tags = taxes
        if not include_caba_tags:
            base_taxes_for_tags = base_taxes_for_tags.filtered(lambda x: x.tax_exigibility != 'on_payment')

        base_rep_lines = base_taxes_for_tags.mapped(
            is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids').filtered(
            lambda x: x.repartition_type == 'base')

        return {
            'base_tags': base_rep_lines.tag_ids.ids + product_tag_ids,
            'taxes': taxes_vals,
            'total_excluded': sign * total_excluded,
            'total_included': sign * currency.round(total_included),
            'total_void': sign * total_void,
        }
    #
    # def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None, fixed_multiplicator=1):
    #     """ Returns the amount of a single tax. base_amount is the actual amount on which the tax is applied, which is
    #         price_unit * quantity eventually affected by previous taxes (if tax is include_base_amount XOR price_include)
    #     """
    #     self.ensure_one()
    #
    #     if self.amount_type == 'fixed':
    #         # Use copysign to take into account the sign of the base amount which includes the sign
    #         # of the quantity and the sign of the price_unit
    #         # Amount is the fixed price for the tax, it can be negative
    #         # Base amount included the sign of the quantity and the sign of the unit price and when
    #         # a product is returned, it can be done either by changing the sign of quantity or by changing the
    #         # sign of the price unit.
    #         # When the price unit is equal to 0, the sign of the quantity is absorbed in base_amount then
    #         # a "else" case is needed.
    #         if base_amount:
    #             return math.copysign(quantity, base_amount) * self.amount * abs(fixed_multiplicator)
    #         else:
    #             return quantity * self.amount * abs(fixed_multiplicator)
    #
    #     price_include = self._context.get('force_price_include', self.price_include)
    #     # base * (1 + tax_amount) = new_base
    #     if self.amount_type == 'percent' and not price_include:
    #         return base_amount * self.amount / 100
    #     # <=> new_base = base / (1 + tax_amount)
    #     if self.amount_type == 'percent' and price_include:
    #         return base_amount - (base_amount / (1 + self.amount / 100))
    #     # base / (1 - tax_amount) = new_base
    #     if self.amount_type == 'division' and not price_include:
    #         return base_amount / (1 - self.amount / 100) - base_amount if (1 - self.amount / 100) else 0.0
    #     # <=> new_base * (1 - tax_amount) = base
    #     if self.amount_type == 'division' and price_include:
    #         return base_amount - (base_amount * (self.amount / 100))
    #     # default value for custom amount_type
    #     if self.amount_type == 'margin_percentage' and not price_include:
    #         result = base_amount * self.amount / 100
    #         return result if result > 0 else 0.0
    #     if self.amount_type == 'margin_percentage' and price_include:
    #         result = base_amount - (base_amount / (1 + self.amount / 100))
    #         return result if result > 0 else 0.0
    #     return 0.0
