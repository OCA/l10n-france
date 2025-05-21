# Copyright 2024 Moka (https://moka.cloud).
# @author Horvat Damien <ultrarushgame@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductCategory(models.Model):

    _inherit = 'product.category'

    vat_on_margin = fields.Boolean(
        string='VAT on Margin',
        help='Check this box if the products in this category are subject to VAT on margin.'
    )