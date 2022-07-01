# © 2022 David BEAL @ Akretion
# © 2022 Alexis DE LATTRE @ Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class ResPartner(models.Model):
    _inherit = "res.partner"

    bpce_factoring_balance = fields.Boolean(
        string="Use BPCE factoring balance",
        groups="account.group_account_invoice",
        company_dependent=True,
        help="Use BPCE factoring receivable balance external service",
    )

    @api.constrains("bpce_factoring_balance", "ref")
    def bpce_ref_constrains(self):
        for rec in self:
            if rec.bpce_factoring_balance and (not rec.ref or not rec.siret):
                raise UserError(
                    "Les balances clients gérées par BPCE doivent avoir "
                    "les champs Référence et SIRET remplis"
                )
