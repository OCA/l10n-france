# -*- coding: utf-8 -*-
# © 2014-2016 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AcountInvoiceLine(models.Model):

    _inherit = 'account.invoice.line'

    subtotal_ecotaxe = fields.Float(
        store=True,
        compute='_compute_ecotaxe',
        oldname="amount_ecotaxe"
    )
    unit_ecotaxe_amount = fields.Float(
        string='ecotaxe', store=True,
        compute='_compute_ecotaxe',
        oldname="amount_ecotaxe"
    )
    ecotaxe_classification_id = fields.Many2one(
        'account.ecotaxe.classification',
        string='Ecotaxe Classification',
     )

    @api.multi
    @api.depends('product_id', 'quantity')
    def _compute_ecotaxe(self):
        for line in self:
            line.unit_ecotaxe_amount = line.product_id.ecotaxe_amount

            if line.invoice_id:
                cur = line.invoice_id.currency_id
                line.unit_ecotaxe_amount= cur.round(
                    line.unit_ecotaxe_amount)

                line.subtotal_ecotaxe = line.unit_ecotaxe_amount * line.quantity  


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
                 'invoice_line_ids.product_id', 'invoice_line_ids.quantity')
    def _compute_ecotaxe(self):
        for invoice in self:
            val_ecotaxe = 0.0
            for line in invoice.invoice_line_ids:
                val_ecotaxe += line.subtotal_ecotaxe
            invoice.amount_ecotaxe = val_ecotaxe
            invoice.amount_untaxed_with_ecotaxe = \
                invoice.amount_untaxed + invoice.amount_ecotaxe
            invoice.amount_tax_without_ecotaxe = \
                invoice.amount_tax - invoice.amount_ecotaxe
