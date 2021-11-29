# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    fr_vat_type = fields.Selection(
        [
            ("france", "France"),
            ("intracom_b2b", "Intra-EU B2B"),
            ("intracom_b2c", "Intra-EU B2C over 10k€ limit"),
            ("extracom", "Extra-EU"),
        ],
        string="Type",
        help="This field is used by the French VAT return module",
    )
