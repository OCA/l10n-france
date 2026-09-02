# Copyright Odoo SA (https://www.odoo.com/)
# Copyright 2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command, models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("fr_oca")
    def _get_fr_oca_template_data(self):
        return {
            "name": "OCA",
            "code_digits": 6,
            "property_account_receivable_id": "fr_pcg_recv",
            "property_account_payable_id": "fr_pcg_pay",
            "property_account_expense_categ_id": "pcg_607",
            "property_account_income_categ_id": "pcg_7071",
            "property_account_downpayment_categ_id": "pcg_4191",
        }

    @template("fr_oca", "res.company")
    def _get_fr_oca_res_company(self):
        return {
            self.env.company.id: {
                "account_fiscal_country_id": "base.fr",
                "bank_account_code_prefix": "512",
                "cash_account_code_prefix": "53",
                "transfer_account_code_prefix": "58",
                "account_default_pos_receivable_account_id": "fr_pcg_recv_pos",
                "income_currency_exchange_account_id": "pcg_766",
                "expense_currency_exchange_account_id": "pcg_666",
                "account_journal_suspense_account_id": "pcg_472",
                "account_journal_early_pay_discount_loss_account_id": "pcg_665",
                "account_journal_early_pay_discount_gain_account_id": "pcg_765",
                "deferred_expense_account_id": "pcg_486",
                "deferred_revenue_account_id": "pcg_487",
                "l10n_fr_rounding_difference_loss_account_id": "pcg_6589",
                "l10n_fr_rounding_difference_profit_account_id": "pcg_7589",
                "account_sale_tax_id": "tva_sale_200",
                "account_purchase_tax_id": "tva_purchase_200",
            },
        }

    @template("fr_oca", "account.journal")
    def _get_fr_oca_account_journal(self):
        return {
            "sale": {"refund_sequence": True},
            "purchase": {"refund_sequence": False},
        }

    @template("fr_oca", "account.reconcile.model")
    def _get_fr_oca_reconcile_model(self):
        return {
            "bank_charges_reconcile_model": {
                "name": "Frais bancaires",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": "pcg_6278",
                            "amount_type": "percentage",
                            "amount_string": "100",
                        }
                    ),
                ],
            },
        }
