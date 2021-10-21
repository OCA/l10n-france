# -*- coding: utf-8 -*-
# © 2014-2021 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models


class AccountInvoiceLine(models.Model):

    _inherit = "account.invoice.line"

    subtotal_ecotaxe = fields.Float(
        store=True, compute="_compute_ecotaxe", oldname="amount_ecotaxe"
    )
    unit_ecotaxe_amount = fields.Float(
        string="ecotaxe Unit.",
        store=True,
        compute="_compute_ecotaxe",
    )

    @api.multi
    @api.depends("product_id", "quantity")
    def _compute_ecotaxe(self):
        for line in self:
            line.unit_ecotaxe_amount = line.product_id.ecotaxe_amount

            if line.invoice_id:
                cur = line.invoice_id.currency_id
                line.unit_ecotaxe_amount = cur.round(line.unit_ecotaxe_amount)

            line.subtotal_ecotaxe = line.unit_ecotaxe_amount * line.quantity


    @api.multi
    def price_unit_with_ecotaxe(self):
        self.ensure_one()
        return self.price_unit + (self.unit_ecotaxe_amount or 0.0)

    @api.multi
    @api.depends('unit_ecotaxe_amount')
    def _compute_price(self):
        for line in self:
            prev_price_unit = line.price_unit
            prev_discount = line.discount
            line.update({
                'price_unit': line.price_unit_with_ecotaxe(),
            })
            super(AccountInvoiceLine, line)._compute_price()
            line.update({
                'price_unit': prev_price_unit,
            })

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    amount_ecotaxe = fields.Float(
        string="Included Ecotaxe", store=True, compute="_compute_ecotaxe"
    )

    @api.multi
    @api.depends("invoice_line.subtotal_ecotaxe")
    def _compute_ecotaxe(self):
        for invoice in self:
            val_ecotaxe = 0.0
            for line in invoice.invoice_line:
                val_ecotaxe += line.subtotal_ecotaxe
            invoice.amount_ecotaxe = val_ecotaxe


class AccountInvoiceTax(models.Model):
    _inherit = "account.invoice.tax"

    @api.v8
    def compute(self, invoice):
        vals = {}
        for line in invoice.invoice_line:
            vals[line] = {
                'price_unit': line.price_unit,
                'discount': line.discount,
            }
            line.update({
                'price_unit': line.price_unit_with_ecotaxe(),
                'discount': 0.0,
            })
        res = super(AccountInvoiceTax, self).compute(invoice)
        for line in invoice.invoice_line:
            line.update(vals[line])
        return res
