# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
#    Copyright (C) 2015-TODAY Akretion <http://www.akretion.com>.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
__author__ = 'mourad.elhadj.mimoune'

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
            val_ecotaxe = val1 = 0.0
            cur = invoice.currency_id
            for line in invoice.invoice_line:
                val_ecotaxe += line.amount_ecotaxe
            invoice.amount_ecotaxe = val_ecotaxe
            invoice.amount_untaxed_with_ecotaxe = \
                invoice.amount_untaxed + invoice.amount_ecotaxe
            invoice.amount_tax_without_ecotaxe = \
                invoice.amount_tax - invoice.amount_ecotaxe
