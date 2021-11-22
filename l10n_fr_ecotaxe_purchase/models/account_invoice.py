# -*- coding: utf-8 -*-
# Copyright 2021 Akretion - Mourad EL HADJ MIMOUNE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def _prepare_invoice_line_from_po_line(self, line):
        vals = super(AccountInvoice,
                     self)._prepare_invoice_line_from_po_line(line)
        vals['unit_ecotaxe_amount'] = line.unit_ecotaxe_amount
        return vals
