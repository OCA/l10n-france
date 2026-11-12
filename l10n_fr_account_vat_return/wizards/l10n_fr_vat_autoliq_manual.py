# Copyright 2024 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class L10nFrVatAutoliqManual(models.TransientModel):
    _name = "l10n.fr.vat.autoliq.manual"
    _description = "FR VAT Return: ask product or service for autoliquidation lines"

    fr_vat_return_id = fields.Many2one(
        "l10n.fr.account.vat.return",
        string="FR VAT Return",
        readonly=True,
        required=True,
    )
    line_ids = fields.One2many("l10n.fr.vat.autoliq.manual.line", "parent_id")

    def run(self):
        for line in self.line_ids:
            if line.option == "product":
                vals = {"product_ratio": 100}
            elif line.option == "service":
                vals = {"product_ratio": 0}
            elif line.option == "mix":
                vals = {"product_ratio": line.product_ratio}
            else:
                raise UserError(
                    _("You must select product or service for journal item '%s'.")
                    % line.move_line_id.display_name
                )
            line.autoliq_line_id.write(vals)
        self.fr_vat_return_id.write({"autoliq_manual_done": True})
        self.fr_vat_return_id.manual2auto()


class L10nFrVatAutoliqManualLine(models.TransientModel):
    _name = "l10n.fr.vat.autoliq.manual.line"
    _description = "FR VAT Return: ask product or service on specific journal items"

    parent_id = fields.Many2one("l10n.fr.vat.autoliq.manual", ondelete="cascade")
    autoliq_line_id = fields.Many2one(
        "l10n.fr.account.vat.return.autoliq.line", required=True
    )
    move_line_id = fields.Many2one(related="autoliq_line_id.move_line_id")
    journal_id = fields.Many2one(related="move_line_id.journal_id")
    date = fields.Date(related="move_line_id.date")
    partner_id = fields.Many2one(related="move_line_id.partner_id")
    account_id = fields.Many2one(related="move_line_id.account_id")
    ref = fields.Char(related="move_line_id.move_id.ref")
    label = fields.Char(related="move_line_id.name")
    company_currency_id = fields.Many2one(related="move_line_id.company_currency_id")
    debit = fields.Monetary(
        related="move_line_id.debit", currency_field="company_currency_id"
    )
    credit = fields.Monetary(
        related="move_line_id.credit", currency_field="company_currency_id"
    )
    option = fields.Selection(
        [
            ("product", "Product"),
            ("service", "Service"),
            ("mix", "Mix"),
        ],
        string="Product or Service",
    )
    product_ratio = fields.Float(digits=(16, 2), string="Product Ratio (%)")
    autoliq_type = fields.Selection(related="autoliq_line_id.autoliq_type")
