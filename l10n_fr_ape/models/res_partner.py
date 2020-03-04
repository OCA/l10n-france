# Copyright 2020 MonsieurB <monsieurb@saaslys.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartnerIndustry(models.Model):
    _inherit = "res.partner.industry"

    code = fields.Char(string='Code')

