# -*- coding: utf-8 -*-
# © 2011 Numérigraphe SARL.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2011 Numérigraphe SARL.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields


class Partner(models.Model):
    """Add the French APE (official main activity of the company)"""
    _inherit = 'res.partner'

    ape_id = fields.Many2one(
        'res.partner.category', string='APE',
        help="If the partner is a French company, enter its official "
        "main activity in this field. The APE is chosen among the "
        "NAF nomenclature.")
