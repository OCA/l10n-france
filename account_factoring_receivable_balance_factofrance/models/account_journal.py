# © 2024 Open Source Integrators, Daniel Reis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    factor_type = fields.Selection(
        selection_add=[("factofrance", "FactoFrance")],
        ondelete={"factofrance": "set null"},
    )
    partner_identification_type = fields.Selection(
        selection=[("1", "1 SIRET"), ("4", "4 TVA")],
    )
