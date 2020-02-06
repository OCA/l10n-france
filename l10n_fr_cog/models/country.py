# -*- coding: utf-8 -*-
# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCountry(models.Model):
    _inherit = 'res.country'

    fr_cog = fields.Integer(
        string=u'Code Officiel Géographique',
        help=u"Code Officiel Géographique, by INSEE")
