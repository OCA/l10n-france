# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nFrAccountVatReturnReimbursement(models.TransientModel):
    _name = "l10n.fr.account.vat.return.reimbursement"
    _description = "FR VAT Reimbursement (3519)"

    return_id = fields.Many2one(
        "l10n.fr.account.vat.return", readonly=True, required=True, string="VAT Return"
    )
    company_currency_id = fields.Many2one(related="return_id.company_id.currency_id")
    min_amount = fields.Integer(related="return_id.reimbursement_min_amount")
    vat_credit_total = fields.Integer(related="return_id.vat_credit_total")
    amount = fields.Integer(string="Reimbursement Amount", required=True)
    reimbursement_type = fields.Selection(
        "_reimbursement_type_selection", required=True
    )
    first_creation_date = fields.Date(string="Creation Date")
    end_date = fields.Date(string="Event Date")
    reimbursement_comment_dgfip = fields.Text(string="Comment for DGFIP")

    def validate(self):
        self.ensure_one()
        speedy = self.return_id._prepare_speedy()
        if self.amount < self.min_amount:
            raise UserError(
                _(
                    "The reimbursement amount (%d €) cannot be under the minimum amount (%d €)."
                )
                % (self.amount, self.min_amount)
            )
        if self.amount > self.vat_credit_total:
            raise UserError(
                _(
                    "The reimbursement amount (%d €) cannot be superior to the "
                    "amount of the VAT credit (%d €)."
                )
                % (self.amount, self.vat_credit_total)
            )
        today = fields.Date.context_today(self)
        if self.reimbursement_type == "first":
            if not self.first_creation_date:
                raise UserError(_("Creation Date is not set."))
            if self.first_creation_date >= today:
                raise UserError(_("The creation date must be in the past."))
        elif self.reimbursement_type == "end":
            if not self.end_date:
                raise UserError(_("Event Date is not set."))
            if self.end_date >= today:
                raise UserError(_("The event date must be in the past."))
        self.return_id.message_post(
            body=_("Credit VAT reimbursement of %d € submitted.") % self.amount
        )
        self.return_id.create_reimbursement_line(self.amount)
        self.return_id._delete_move_and_attachments()
        move = self.return_id._create_draft_account_move(speedy)
        self.return_id.write(self._prepare_return_write(move.id))

    def _prepare_return_write(self, move_id):
        vals = {
            "reimbursement_type": self.reimbursement_type,
            "move_id": move_id,
            "reimbursement_comment_dgfip": self.reimbursement_comment_dgfip,
        }
        if self.reimbursement_type == "first":
            vals["reimbursement_first_creation_date"] = self.first_creation_date
        elif self.reimbursement_type == "end":
            vals["reimbursement_end_date"] = self.end_date
        return vals

    @api.model
    def _reimbursement_type_selection(self):
        return self.env["l10n.fr.account.vat.return"]._reimbursement_type_selection()
