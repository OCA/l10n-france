# Copyright 2011-2022 Numérigraphe SARL.
# Copyright 2014-2022 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


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
