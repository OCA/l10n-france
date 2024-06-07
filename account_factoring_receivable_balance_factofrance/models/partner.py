# © 2024 Open Source Integrators, Daniel Reis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.constrains("factor_journal_id", "ref", "siret")
    def _constrains_factor_journal_id(self):
        for rec in self:
            is_factofrance = rec.factor_journal_id == "factofrance"
            if is_factofrance and (not rec.ref or not rec.siret):
                msg = _(
                    "Les balances clients gérées par FactoFrance doivent avoir "
                    "les champs Référence et SIRET remplis"
                )
                raise UserError(msg)
