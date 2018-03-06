# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ChorusFlow(models.Model):
    _inherit = 'chorus.flow'

    syntax = fields.Selection(selection_add=[('xml_cii', 'CII 16B XML')])

    @api.model
    def syntax_odoo2chorus(self):
        res = super(ChorusFlow, self).syntax_odoo2chorus()
        res['xml_cii'] = 'IN_DP_E1_CII'
        # TODO will certainly need to be changed for CII 16B
        # Check specs when CII 16B will be put in production by Chorus
        # (scheduled for Chorus release 1.3.3 IT3)
        return res
