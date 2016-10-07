# -*- coding: utf-8 -*-
# © 2011 Numérigraphe SARL.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class Partner(models.Model):
    """Add the French APE (official main activity of the company)"""
    _inherit = 'res.partner'

    ape_id = fields.Many2one(
        'res.partner.category', string='APE',
        help="If the partner is a French company, enter its official "
        "main activity in this field. The APE is chosen among the "
        "NAF nomenclature.")
