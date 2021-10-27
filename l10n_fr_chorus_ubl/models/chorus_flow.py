# -*- coding: utf-8 -*-
# Copyright 2018-2020 Akretion France (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ChorusFlow(models.Model):
    _inherit = 'chorus.flow'

    syntax = fields.Selection(selection_add=[('xml_ubl', 'UBL XML')])

    @api.model
    def syntax_odoo2chorus(self):
        res = super(ChorusFlow, self).syntax_odoo2chorus()
        res['xml_ubl'] = 'IN_DP_E1_UBL_INVOICE'
        return res
