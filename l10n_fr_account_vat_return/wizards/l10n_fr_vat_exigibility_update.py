# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nFrVatExigibilityUpdate(models.TransientModel):
    _name = "l10n.fr.vat.exigibility.update"
    _description = "Change Company VAT Exigibility"

    company_id = fields.Many2one("res.company", required=True, readonly=True)
    current_fr_vat_exigibility = fields.Selection(
        related="company_id.fr_vat_exigibility", string="Current VAT Exigibility"
    )
    new_fr_vat_exigibility = fields.Selection(
        "_fr_vat_exigibility_selection", string="New VAT Exigibility", required=True
    )
    update_type = fields.Selection(
        [
            ("from_start", "From the Start"),
            ("date", "Since Specific Date"),
        ],
        default="from_start",
        required=True,
        string="Update",
    )
    update_date = fields.Date(default=fields.Date.context_today, string="Update Since")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        company = self.env["res.company"].browse(res["company_id"])
        switch = {"on_invoice": "on_payment", "on_payment": "on_invoice"}
        if company.fr_vat_exigibility and company.fr_vat_exigibility in switch:
            res["new_fr_vat_exigibility"] = switch[company.fr_vat_exigibility]
        return res

    @api.model
    def _fr_vat_exigibility_selection(self):
        return self.env["res.company"]._fr_vat_exigibility_selection()

    def run(self):
        self.ensure_one()
        if self.current_fr_vat_exigibility == self.new_fr_vat_exigibility:
            raise UserError(
                _(
                    "If you don't want to change the VAT Exigibility of company '%s', "
                    "click on the Cancel button."
                )
                % self.company_id.display_name
            )
        self.company_id.write({"fr_vat_exigibility": self.new_fr_vat_exigibility})
        domain = [
            ("company_id", "=", self.company_id.id),
            ("move_type", "in", ("out_invoice", "out_refund")),
        ]
        if self.update_type == "date":
            today = fields.Date.context_today(self)
            if self.update_date > today:
                raise UserError(_("The date cannot be in the future."))
            domain += [
                "|",
                ("invoice_date", "=", False),
                ("invoice_date", ">=", self.update_date),
            ]
        moves_to_update = self.env["account.move"].search(domain)
        if self.new_fr_vat_exigibility == "auto":
            for move in moves_to_update:
                vat_on_payment = move._fr_vat_exigibility_auto_compute_vat_on_payment()
                move.write({"out_vat_on_payment": vat_on_payment})
        elif self.new_fr_vat_exigibility == "on_invoice":
            moves_to_update.write({"out_vat_on_payment": False})
        elif self.new_fr_vat_exigibility == "on_payment":
            moves_to_update.write({"out_vat_on_payment": True})
        else:
            raise UserError(_("Wrong value for the new VAT exigibility."))
