# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    fr_vat_periodicity = fields.Selection(
        related="company_id.fr_vat_periodicity", readonly=False
    )
    fr_vat_exigibility = fields.Selection(
        related="company_id.fr_vat_exigibility",
        readonly=True
        # value is updated by the wizard l10n.fr.vat.exigibility.update
    )
    fr_vat_update_lock_dates = fields.Boolean(
        related="company_id.fr_vat_update_lock_dates", readonly=False
    )
    fr_vat_journal_id = fields.Many2one(
        related="company_id.fr_vat_journal_id",
        readonly=False,
        domain="[('company_id', '=', company_id), ('type', '=', 'general')]",
    )
    fr_vat_expense_analytic_distribution = fields.Json(
        related="company_id.fr_vat_expense_analytic_distribution",
        readonly=False,
    )
    fr_vat_income_analytic_distribution = fields.Json(
        related="company_id.fr_vat_income_analytic_distribution",
        readonly=False,
    )
    analytic_precision = fields.Integer(related="company_id.analytic_precision")
    fr_vat_bank_account_id = fields.Many2one(
        related="company_id.fr_vat_bank_account_id",
        readonly=False,
        domain="[('partner_id','=', fr_vat_company_partner_id), "
        "'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    fr_vat_company_partner_id = fields.Many2one(related="company_id.partner_id")
