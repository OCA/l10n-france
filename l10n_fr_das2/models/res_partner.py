# Copyright 2020-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    fr_das2_type = fields.Selection(
        [
            ("fee", "Honoraires et vacations"),
            ("commission", "Commissions"),
            ("brokerage", "Courtages"),
            ("discount", "Ristournes"),
            ("attendance_fee", "Jetons de présence"),
            ("copyright_royalties", "Droits d'auteur"),
            ("licence_royalties", "Droits d'inventeur"),
            ("other_income", "Autre rémunérations"),
            ("allowance", "Indemnités et remboursements"),
        ],
        string="DAS2 Type",
        tracking=100,
    )
    fr_das2_job = fields.Char(
        string="DAS2 Job", size=30, help="Used in the field 'Profession' of DAS2."
    )
