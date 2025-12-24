# Copyright 2017-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _cii_get_party_identification(self, commercial_partner):
        res = super()._cii_get_party_identification(commercial_partner)
        fr_country_codes = self.env["res.company"]._get_france_country_codes()
        if (
            commercial_partner.company_registry
            and commercial_partner.country_id
            and commercial_partner.country_id.code in fr_country_codes
        ):
            res["0002"] = commercial_partner.company_registry
        return res
