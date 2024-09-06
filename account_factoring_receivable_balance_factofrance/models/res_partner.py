# © 2024 Open Source Integrators, Daniel Reis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, exceptions, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.constrains("factor_journal_id", "ref", "siret")
    def _constrains_factor_journal_id(self):
        partners_missing_ref = self.filtered(
            lambda x: x.factor_journal_id.factor_type == "factofrance" and not x.ref
        )
        if partners_missing_ref:
            raise exceptions.UserError(
                _(
                    "Les balances clients gérées par FactoFrance doivent avoir "
                    "le champ Référence rempli."
                )
            )
