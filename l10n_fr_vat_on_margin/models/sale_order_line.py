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
        precompute=True,
    )

    line_concerned_by_margin = fields.Boolean(
        string='Line Concerned by Margin',
        compute='_compute_line_concerned_by_margin',
        store=True,
    )

    @api.depends('tax_id')
    def _compute_line_concerned_by_margin(self):
        for line in self:
            if line.tax_id.filtered(lambda tax: tax.vat_on_margin):
                line.line_concerned_by_margin = True

    @api.onchange('product_id')
    def _onchange_product_id_warning_margin(self):
        if self.product_id.vat_on_margin or self.product_id.categ_id.vat_on_margin:
            if self.order_id.fiscal_position_id != self.env['account.fiscal.position'].search(
                [('name', '=', 'TVA sur marge')], limit=1):
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _(
                            'This order is concerned by VAT on margin. You should select the VAT on margin fiscal position.')
                    }
                }

    @api.depends('purchase_price', 'price_unit', 'product_uom_qty')
    def _compute_margin_untaxed(self):
        for line in self:
            line.margin_amount_untaxed = (line.price_unit - line.purchase_price)

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        price_unit_margin = 0.0
        if self.line_concerned_by_margin:
            price_unit_margin = (self.price_unit - self.purchase_price)
        result = self.env['account.tax']._convert_to_tax_base_line_dict(
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
        print("=== result ===", result)
        return result

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
            'margin_amount': self.margin_amount_untaxed,
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

    # SALE PURCHASE

    def _purchase_service_prepare_order_values(self, supplierinfo):
        """ Returns the values to create the purchase order from the current SO line.
            :param supplierinfo: record of product.supplierinfo
            :rtype: dict
        """
        self.ensure_one()
        partner_supplier = supplierinfo.partner_id
        fpos = self.env['account.fiscal.position'].sudo()._get_fiscal_position(partner_supplier)
        if self.line_concerned_by_margin:
            print("=== Passage ici fiscal position", fpos)
            fpos = self.order_id.fiscal_position_id
        date_order = self._purchase_get_date_order(supplierinfo)
        return {
            'partner_id': partner_supplier.id,
            'partner_ref': partner_supplier.ref,
            'company_id': self.company_id.id,
            'currency_id': partner_supplier.property_purchase_currency_id.id or self.env.company.currency_id.id,
            'dest_address_id': False,  # False since only supported in stock
            'origin': self.order_id.name,
            'payment_term_id': partner_supplier.property_supplier_payment_term_id.id,
            'date_order': date_order,
            'fiscal_position_id': fpos.id,
        }

    def _purchase_service_prepare_line_values(self, purchase_order, quantity=False):
        """ Returns the values to create the purchase order line from the current SO line.
            :param purchase_order: record of purchase.order
            :rtype: dict
            :param quantity: the quantity to force on the PO line, expressed in SO line UoM
        """
        self.ensure_one()
        # compute quantity from SO line UoM
        product_quantity = self.product_uom_qty
        if quantity:
            product_quantity = quantity

        purchase_qty_uom = self.product_uom._compute_quantity(product_quantity, self.product_id.uom_po_id)

        # determine vendor (real supplier, sharing the same partner as the one from the PO, but with more accurate informations like validity, quantity, ...)
        # Note: one partner can have multiple supplier info for the same product
        supplierinfo = self.product_id._select_seller(
            partner_id=purchase_order.partner_id,
            quantity=purchase_qty_uom,
            date=purchase_order.date_order and purchase_order.date_order.date(),  # and purchase_order.date_order[:10],
            uom_id=self.product_id.uom_po_id
        )
        supplier_taxes = self.product_id.supplier_taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes = purchase_order.fiscal_position_id.map_tax(supplier_taxes)

        # compute unit price
        price_unit = 0.0
        product_ctx = {
            'lang': get_lang(self.env, purchase_order.partner_id.lang).code,
            'company_id': purchase_order.company_id,
        }
        if supplierinfo:
            price_unit = self.env['account.tax'].sudo()._fix_tax_included_price_company(
                supplierinfo.price, supplier_taxes, taxes, self.company_id)
            if purchase_order.currency_id and supplierinfo.currency_id != purchase_order.currency_id:
                price_unit = supplierinfo.currency_id._convert(price_unit, purchase_order.currency_id,
                                                               purchase_order.company_id,
                                                               fields.Date.context_today(self))
            product_ctx.update({'seller_id': supplierinfo.id})
        else:
            product_ctx.update({'partner_id': purchase_order.partner_id.id})

        product = self.product_id.with_context(**product_ctx)
        name = product.display_name
        if product.description_purchase:
            name += '\n' + product.description_purchase

        line_description = self.with_context(
            lang=self.order_id.partner_id.lang)._get_sale_order_line_multiline_description_variants()
        if line_description:
            name += line_description

        return {
            'name': name,
            'product_qty': purchase_qty_uom,
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_po_id.id,
            'price_unit': price_unit,
            'margin_amount': self.margin_amount_untaxed,
            'date_planned': fields.Date.from_string(purchase_order.date_order) + relativedelta(
                days=int(supplierinfo.delay)),
            'taxes_id': [(6, 0, taxes.ids)],
            'order_id': purchase_order.id,
            'sale_line_id': self.id,
        }

    def _purchase_service_get_company(self):
        return self.company_id

    def _purchase_service_match_supplier(self, warning=True):
        # determine vendor of the order (take the first matching company and product)
        suppliers = self.product_id._select_seller(partner_id=self._retrieve_purchase_partner(),
                                                   quantity=self.product_uom_qty, uom_id=self.product_uom)
        if warning and not suppliers:
            raise UserError(
                _("There is no vendor associated to the product %s. Please define a vendor for this product.",
                  self.product_id.display_name))
        return suppliers[0]

    def _purchase_service_match_purchase_order(self, partner, company=False):
        if self.line_concerned_by_margin:
            return self.env['purchase.order'].search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'draft'),
                ('company_id', '=', (company and company or self.env.company).id),
                ('origin', '=', self.order_id.name),
            ], order='id desc')
        else:
            return self.env['purchase.order'].search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'draft'),
                ('company_id', '=', (company and company or self.env.company).id),
            ], order='id desc')

    def _create_purchase_order(self, supplierinfo):
        values = self._purchase_service_prepare_order_values(supplierinfo)
        return self.env['purchase.order'].with_context(mail_create_nosubscribe=True).create(values)

    def _match_or_create_purchase_order(self, supplierinfo):
        purchase_order = self._purchase_service_match_purchase_order(supplierinfo.partner_id)[:1]
        print("=== purchase_order ===", purchase_order, self, supplierinfo, self.line_concerned_by_margin,
              self.order_id.fiscal_position_id)
        if not purchase_order:
            purchase_order = self._create_purchase_order(supplierinfo)
        return purchase_order

    def _retrieve_purchase_partner(self):
        """ In case we want to explicitely name a partner from whom we want to buy or receive products
        """
        self.ensure_one()
        return False

    def _purchase_service_create(self, quantity=False):
        """ On Sales Order confirmation, some lines (services ones) can create a purchase order line and maybe a purchase order.
            If a line should create a RFQ, it will check for existing PO. If no one is find, the SO line will create one, then adds
            a new PO line. The created purchase order line will be linked to the SO line.
            :param quantity: the quantity to force on the PO line, expressed in SO line UoM
        """
        supplier_po_map = {}
        sale_line_purchase_map = {}

        for line in self:
            line = line.with_company(line._purchase_service_get_company())
            supplierinfo = line._purchase_service_match_supplier()
            partner_supplier = supplierinfo.partner_id

            # determine (or create) PO
            purchase_order = supplier_po_map.get(partner_supplier.id)
            if not purchase_order:
                purchase_order = line._match_or_create_purchase_order(supplierinfo)
            so_name = line.order_id.name
            origins = (purchase_order.origin or '').split(', ')
            if so_name not in origins:
                purchase_order.write({'origin': ', '.join(origins + [so_name])})
            supplier_po_map[partner_supplier.id] = purchase_order

            # add a PO line to the PO
            values = line._purchase_service_prepare_line_values(purchase_order, quantity=quantity)
            purchase_line = line.env['purchase.order.line'].create(values)

            # link the generated purchase to the SO line
            sale_line_purchase_map.setdefault(line, line.env['purchase.order.line'])
            sale_line_purchase_map[line] |= purchase_line
        return sale_line_purchase_map

    def _purchase_service_generation(self):
        """ Create a Purchase for the first time from the sale line. If the SO line already created a PO, it
            will not create a second one.
        """
        sale_line_purchase_map = {}
        for line in self:
            line = line.with_company(line._purchase_service_get_company())
            # Do not regenerate PO line if the SO line has already created one in the past (SO cancel/reconfirmation case)
            if line.product_id.service_to_purchase and not line.purchase_line_count:
                result = line._purchase_service_create()
                sale_line_purchase_map.update(result)
        return sale_line_purchase_map
