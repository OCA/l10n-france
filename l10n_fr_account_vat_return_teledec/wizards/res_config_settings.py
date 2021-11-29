# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    fr_vat_teledec_legal_representative_id = fields.Many2one(
        related="company_id.fr_vat_teledec_legal_representative_id", readonly=False
    )
    fr_vat_teledec_legal_form = fields.Selection(
        related="company_id.fr_vat_teledec_legal_form", readonly=False
    )
    fr_vat_teledec_email = fields.Char(
        related="company_id.fr_vat_teledec_email", readonly=False
    )
    fr_vat_teledec_test_mode = fields.Boolean(
        related="company_id.fr_vat_teledec_test_mode", readonly=False
    )
