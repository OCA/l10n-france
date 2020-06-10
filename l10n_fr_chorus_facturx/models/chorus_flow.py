# Copyright 2018 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ChorusFlow(models.Model):
    _inherit = "chorus.flow"

    syntax = fields.Selection(
        selection_add=[("xml_cii", "CII 16B XML"), ("pdf_factur-x", "Factur-X PDF"),]
    )

    @api.model
    def syntax_odoo2chorus(self):
        res = super().syntax_odoo2chorus()
        res["xml_cii"] = "IN_DP_E1_CII_16B"
        res["pdf_factur-x"] = "IN_DP_E2_CII_FACTURX"
        # https://communaute.chorus-pro.gouv.fr/wp-content/uploads/2018/04/AIFE-Chorus-Pro-Qualification-Note-de-livraison-V1.3.3-IT3.pdf
        # page 14
        return res
