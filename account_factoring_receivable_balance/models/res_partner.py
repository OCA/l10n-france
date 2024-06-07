# © 2024 Open Source Integrators, Daniel Reis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    factor_journal_id = fields.Many2one(
        comodel_name="account.journal",
        help="Select the factoring service for this partner.",
    )
