# Copyright 2011-2021 Numérigraphe SARL.
# Copyright 2014-2021 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # siret field is defined in l10n_fr module on res.partner
    # with an unstored related field on res.company
    siret = fields.Char(store=True, readonly=True)
    siren = fields.Char(
        string="SIREN", related="partner_id.siren", store=True, readonly=False
    )
    nic = fields.Char(
        string="NIC", related="partner_id.nic", store=True, readonly=False
    )
    # company_registry field is definied in base module on res.company
    company_registry = fields.Char(
        string="Company Registry",
        related="partner_id.company_registry",
        store=True,
        readonly=False,
    )
    # l10n_fr defines this field on res.company from 16.0 on; it does not exist
    # on 15.0, so carry it here — same name and semantics, on the country code
    # list _get_france_country_codes() returns on this version.
    is_france_country = fields.Boolean(
        compute="_compute_is_france_country",
        string="Is Part of DOM-TOM",
    )

    @api.depends("country_id")
    def _compute_is_france_country(self):
        fr_country_codes = self._get_france_country_codes()
        for company in self:
            company.is_france_country = company.country_id.code in fr_country_codes
