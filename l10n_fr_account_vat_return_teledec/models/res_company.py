# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    fr_vat_teledec_legal_representative_id = fields.Many2one(
        "res.partner",
        string="Legal Representative",
        ondelete="restrict",
        domain=[("is_company", "=", False)],
    )
    fr_vat_teledec_legal_form = fields.Selection(
        [
            ("ASS", "Association"),
            ("ARL", "EARL"),
            ("EI", "EI"),
            ("EIR", "EIRL"),
            ("ERL", "EURL"),
            ("GEC", "GAEC"),
            ("GIE", "GIE"),
            ("SA", "SA"),
            ("SAS", "SAS"),
            ("SASU", "SASU"),
            ("SRL", "SARL"),
            ("SEA", "SCEA"),
            ("SCI", "SCI"),
            ("SCM", "SCM"),
            ("SLR", "SELARL"),
            ("SNC", "SNC"),
            ("ZZZ", "Other"),
        ],
        string="Company Legal Form",
    )
    fr_vat_teledec_email = fields.Char(
        "E-mail for Teledec.fr",
        help="Must correspond to your login on the Teledec.fr website",
    )
    fr_vat_teledec_test_mode = fields.Boolean(
        string="Teledec.fr Test Mode",
        help="If active, the request will be sent to the test serveur of "
        "Teledec.fr and nothing will be retransmitted to DGFIP.",
    )
