# -*- coding: utf-8 -*-
# © 2014-2016 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models


class AcountInvoiceLine(models.Model):

    _inherit = 'account.invoice.line'

    amount_ecotaxe = fields.Float(string='Ecotaxe', store=True,
                                  compute='_compute_ecotaxe')

    @api.multi
    @api.depends('invoice_line_tax_id', 'product_id', 'quantity')
    def _compute_ecotaxe(self):
        for line in self:
            ecotaxe_id = [tax.id for tax in line.invoice_line_tax_id
                          if tax.is_ecotaxe]
            ecotaxe_id = self.env['account.tax'].browse(ecotaxe_id)
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            val = 0.0
            if ecotaxe_id:
                taxes = ecotaxe_id.compute_all(
                    price, line.quantity,
                    product=line.product_id,
                    partner=line.invoice_id.partner_id)['taxes']

                for t in taxes:
                    val += t.get('amount', 0.0)
            line.amount_ecotaxe = val

        if line.invoice_id:
            cur = line.invoice_id.currency_id
            line.amount_ecotaxe = cur.round(
                line.amount_ecotaxe)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    amount_untaxed_with_ecotaxe = fields.Float('Untaxed Amount with Ecotaxe',
                                               store=True,
                                               compute='_compute_ecotaxe')
    amount_ecotaxe = fields.Float(string='Included Ecotaxe', store=True,
                                  compute='_compute_ecotaxe')
    amount_tax_without_ecotaxe = fields.Float(string='Other Taxes', store=True,
                                              compute='_compute_ecotaxe')

    @api.multi
    @api.depends('amount_untaxed', 'amount_tax',
                 'invoice_line.invoice_line_tax_id',
                 'invoice_line.product_id', 'invoice_line.quantity')
    def _compute_ecotaxe(self):
        for invoice in self:
            val_ecotaxe = 0.0
            for line in invoice.invoice_line:
                val_ecotaxe += line.amount_ecotaxe
            invoice.amount_ecotaxe = val_ecotaxe
            invoice.amount_untaxed_with_ecotaxe = \
                invoice.amount_untaxed + invoice.amount_ecotaxe
            invoice.amount_tax_without_ecotaxe = \
                invoice.amount_tax - invoice.amount_ecotaxe
