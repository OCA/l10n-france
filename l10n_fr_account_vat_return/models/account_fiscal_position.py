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
            ("france_exo", "France Exonerated"),
        ],
        string="Type",
        help="This field is used by the French VAT return module",
    )


class AccountFiscalPositionTemplate(models.Model):
    _inherit = "account.fiscal.position.template"

    fr_vat_type = fields.Selection(
        [
            ("france", "France"),
            ("intracom_b2b", "Intra-EU B2B"),
            ("intracom_b2c", "Intra-EU B2C over 10k€ limit"),
            ("extracom", "Extra-EU"),
        ],
        string="Type",
    )


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _get_fp_vals(self, company, position):
        vals = super()._get_fp_vals(company, position)
        vals["fr_vat_type"] = position.fr_vat_type
        return vals
