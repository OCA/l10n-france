# Copyright 2024 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.tools.misc import format_date


class L10nFrVatDraftMoveOption(models.TransientModel):
    _name = "l10n.fr.vat.draft.move.option"
    _description = "FR VAT Return: show or continue"

    fr_vat_return_id = fields.Many2one(
        "l10n.fr.account.vat.return", string="FR VAT Return", readonly=True
    )
    end_date = fields.Date(related="fr_vat_return_id.end_date")
    draft_move_ids = fields.Many2many(
        "account.move", string="Draft Journal Entries", readonly=True
    )
    draft_move_count = fields.Integer(readonly=True)

    def option_show(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_journal_line"
        )
        if len(self.draft_move_ids) == 1:
            action.update(
                {
                    "views": False,
                    "view_id": False,
                    "view_mode": "form,tree,kanban",
                    "res_id": self.draft_move_ids.id,
                }
            )
        else:
            action.update(
                {
                    "domain": [("id", "in", self.draft_move_ids.ids)],
                    "context": {
                        "search_default_posted": False,
                        "default_move_type": "entry",
                        "view_no_maturity": True,
                    },
                }
            )
        return action

    def option_continue(self):
        self.ensure_one()
        self.fr_vat_return_id.write({"ignore_draft_moves": True})
        self.fr_vat_return_id.message_post(
            body=_(
                "Ignoring %(count)s draft journal entries dated before %(end_date)s.",
                count=self.draft_move_count,
                end_date=format_date(self.env, self.end_date),
            )
        )
        return self.fr_vat_return_id.manual2auto()
