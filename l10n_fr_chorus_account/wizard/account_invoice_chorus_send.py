# Copyright 2018-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class AccountInvoiceChorusSend(models.TransientModel):
    _name = "account.invoice.chorus.send"
    _description = "Send several invoices to Chorus"
    _check_company_auto = True

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        assert self._context.get("active_ids"), "Missing active_ids in ctx"
        invoices = self.env["account.move"].browse(self._context.get("active_ids"))
        company = False
        for invoice in invoices:
            if invoice.move_type not in ("out_invoice", "out_refund"):
                raise UserError(
                    _(
                        "Move '%s' is not a customer invoice. You can only send "
                        "customer invoices/refunds to Chorus Pro."
                    )
                    % invoice.display_name
                )
            if invoice.state != "posted":
                raise UserError(
                    _(
                        "The state of invoice '%(invoice)s' is "
                        "'%(invoice_state)s'. You can only send to Chorus Pro invoices "
                        "in posted state."
                    )
                    % {
                        "invoice": invoice.display_name,
                        "invoice_state": invoice._fields["state"].convert_to_export(
                            invoice.state, invoice
                        ),
                    }
                )
            if invoice.transmit_method_code != "fr-chorus":
                raise UserError(
                    _(
                        "On invoice '%(invoice)s', the transmit method is "
                        "'%(transmit_method)s'. To be able "
                        "to send it to Chorus Pro, the transmit method must be "
                        "'Chorus Pro'."
                    )
                    % {
                        "invoice": invoice.display_name,
                        "transmit_method": invoice.transmit_method_id.name or _("None"),
                    }
                )
            if invoice.chorus_flow_id:
                raise UserError(
                    _(
                        "The invoice '%(invoice)s' has already been sent: "
                        "it is linked to Chorus Flow %(flow)s."
                    )
                    % {
                        "invoice": invoice.display_name,
                        "flow": invoice.chorus_flow_id.display_name,
                    }
                )
            if company:
                if company != invoice.company_id:
                    raise UserError(
                        _("All the selected invoices must be in the same company")
                    )
            else:
                company = invoice.company_id

        company._check_chorus_invoice_format()
        res.update(
            {
                "invoice_ids": [Command.set(invoices.ids)],
                "invoice_count": len(invoices),
                "company_id": company.id,
            }
        )
        return res

    invoice_ids = fields.Many2many(
        "account.move",
        string="Invoices to Send",
        readonly=True,
        check_company=True,
    )
    invoice_count = fields.Integer(string="Number of Invoices", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    chorus_invoice_format = fields.Selection(
        related="company_id.fr_chorus_invoice_format"
    )

    def run(self):
        self.ensure_one()
        action = {}
        flow = self.invoice_ids._fr_chorus_send()
        if flow and self._context.get("show_flow"):
            action = self.env["ir.actions.actions"]._for_xml_id(
                "l10n_fr_chorus_account.chorus_flow_action"
            )
            action.update(
                {
                    "view_mode": "form,tree",
                    "views": False,
                    "res_id": flow.id,
                }
            )
        return action
