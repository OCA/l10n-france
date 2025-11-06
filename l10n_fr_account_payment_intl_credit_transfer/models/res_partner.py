# Copyright 2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_transfer_regulatory_reporting_id = fields.Many2one(
        "account.pain.regulatory.reporting",
        company_dependent=True,
        string="Regulatory Reporting for Intl. Credit Transfers",
        help="It will be the default value for the field Regulatory Reporting "
        "of non-SEPA credit transfer payment lines with this partner.",
    )
