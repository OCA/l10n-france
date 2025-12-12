# Copyright 2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount

REGULATORY_REPORTING_REQUIRED_THRESHOLD = 50000


class AccountPaymentLine(models.Model):
    _inherit = "account.payment.line"

    regulatory_reporting_id = fields.Many2one(
        compute="_compute_regulatory_reporting_id",
        store=True,
        readonly=False,
        precompute=True,
    )

    # I can't depend on order_id.sepa because sepa is not a stored field
    # So I set field even on sepa payment order, and we remove the value
    # via the inherit of _prepare_write_draft2open()
    @api.depends(
        "partner_id",
        "order_id.payment_method_line_id",
        "order_id.company_id",
    )
    def _compute_regulatory_reporting_id(self):
        for line in self:
            order = line.order_id
            payment_method = order.payment_method_line_id.payment_method_id
            if (
                line.partner_id
                and order
                and order.company_id
                and payment_method.pain_version
                and payment_method.pain_version.startswith("pain.001.001.")
            ):
                partner = line.partner_id.with_company(order.company_id.id)
                if partner.credit_transfer_regulatory_reporting_id:
                    line.regulatory_reporting_id = (
                        partner.credit_transfer_regulatory_reporting_id.id
                    )

    def _draft2open_payment_line_check(self):
        errors = super()._draft2open_payment_line_check()
        order = self.order_id
        company = order.company_id
        fr_country = self.env.ref("base.fr")
        if (
            company.is_france_country
            and self.regulatory_reporting_id
            and self.regulatory_reporting_id.country_id != fr_country
        ):
            errors.append(
                self.env._(
                    "On payment line %(name)s with partner '%(partner)s', "
                    "the selected Regulatory Reporting '%(regulatory_reporting)s' "
                    "is not a Regulatory Reporting for France.",
                    name=self.name,
                    partner=self.partner_id.display_name,
                    regulatory_reporting=self.regulatory_reporting_id.display_name,
                )
            )
        return errors

    def _prepare_account_payment_vals(self, payment_lot, pay_sequence):
        """I can't handle this check in _draft2open_payment_line_check()
        because we could have several payment lines for the same partner
        each under 50k€ but, once grouped in the same payment, have a payment
        amount > 50 k€
        """
        vals = super()._prepare_account_payment_vals(payment_lot, pay_sequence)
        order = self.order_id
        company = order.company_id
        euro = self.env.ref("base.EUR")
        if (
            not order.sepa
            and order.payment_method_line_id.payment_method_id.pain_version
            and order.payment_method_line_id.payment_method_id.pain_version.startswith(
                "pain.001.001."
            )
            and company.is_france_country
            and company.currency_id == euro
            and not self[:1].regulatory_reporting_id
        ):
            currency = self.env["res.currency"].browse(vals["currency_id"])
            today = fields.Date.context_today(self)
            amount_euro = currency._convert(vals["amount"], euro, company, today)
            if (
                euro.compare_amounts(
                    amount_euro, REGULATORY_REPORTING_REQUIRED_THRESHOLD
                )
                >= 0
            ):
                raise UserError(
                    self.env._(
                        "On the payment of %(amount)s for partner '%(partner)s', "
                        "the field Regulatory Reporting is not set. This "
                        "field is required for non-SEPA payments above %(threshold)s. "
                        "You must set the field Regulatory Reporting on the related "
                        "payment lines.",
                        amount=format_amount(self.env, vals["amount"], currency),
                        partner=self.partner_id.display_name,
                        threshold=format_amount(
                            self.env, REGULATORY_REPORTING_REQUIRED_THRESHOLD, euro
                        ),
                    )
                )

        return vals

    def _prepare_write_draft2open(self):
        vals = super()._prepare_write_draft2open()
        order = self.order_id
        if (
            self.regulatory_reporting_id
            and order.company_id.is_france_country
            and order.sepa
        ):
            vals["regulatory_reporting_id"] = False
        return vals
