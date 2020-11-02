# Copyright 2011 Numérigraphe SARL.
# Copyright 2014-2018 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    """Replace the company's fields for SIRET/RC with the partner's"""

    _inherit = "res.company"

    # siret field is defined in l10n_fr module on res.partner
    # with an unstored related field on res.company
    siret = fields.Char(store=True)
    siren = fields.Char(string="SIREN", related="partner_id.siren", store=True)
    nic = fields.Char(string="NIC", related="partner_id.nic", store=True)
    # company_registry field is definied in base module on res.company
    company_registry = fields.Char(
        string="Company Registry", related="partner_id.company_registry", store=True
    )
