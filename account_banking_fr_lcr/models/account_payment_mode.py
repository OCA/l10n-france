# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentMode(models.Model):
    _inherit = "account.payment.mode"

    fr_lcr_type = fields.Selection(
        [
            ("not_accepted", "Lettre de change non acceptée (LCR directe)"),
            ("accepted", "Lettre de change acceptée"),
            ("promissory_note", "Billet à ordre"),
        ],
        string="LCR Type",
        default="not_accepted",
    )
