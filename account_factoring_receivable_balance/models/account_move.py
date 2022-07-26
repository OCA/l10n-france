# © 2022 David BEAL @ Akretion
# © 2022 Alexis DE LATTRE @ Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools.misc import formatLang, format_date as odoo_format_date, get_lang


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    subrogation_id = fields.Many2one(
        comodel_name="subrogation.receipt",
        string="Subrogation Receipt",
        check_company=True,
    )
    partner_bank_id = fields.Many2one(
        comodel_name="res.bank",
        related="move_id.partner_bank_id.bank_id",
        string="Recipient Bank",
    )
    partner_ref = fields.Char(string="Partn.", compute="_compute_partner_ref")

    def _compute_partner_ref(self):
        for rec in self:
            if rec.partner_id:
                rec.partner_ref = rec.partner_id.commercial_partner_id.ref
            else:
                rec.partner_ref = ""
