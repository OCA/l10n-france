# Copyright 2016-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models
from odoo.exceptions import UserError


class AccountPaymentLine(models.Model):
    _inherit = "account.payment.line"

    def _compute_payment_line(self):
        res = super()._compute_payment_line()
        for line in self:
            if (
                line.order_id.payment_method_line_id.payment_method_id.code == "fr_lcr"
                and line.move_line_id
                and line.move_line_id.move_id.fr_lcr_partner_bank_id
            ):
                line.partner_bank_id = (
                    line.move_line_id.move_id.fr_lcr_partner_bank_id.id
                )
        return res

    def draft2open_payment_line_check(self):
        res = super().draft2open_payment_line_check()
        if self.order_id.payment_method_code == "fr_lcr":
            eur_currency_id = self.env.ref("base.EUR").id
            if self.currency_id.id != eur_currency_id:
                raise UserError(
                    self.env._(
                        "The currency of payment line '%(payment_line)s' is "
                        "%(currency)s. To be included in a french bill of exchange, "
                        "the currency must be EUR.",
                        payment_line=self.display_name,
                        currency=self.currency_id.name,
                    )
                )
            self.partner_bank_id._fr_iban_validate()
        return res
