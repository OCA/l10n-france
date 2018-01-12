# -*- coding: utf-8 -*-
# Copyright (C) 2018 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.multi
    def get_certification_information(self):
        """This function is made to allow overload for custom module
        like 'pos_order_load'"""
        return self.read(['pos_reference', 'l10n_fr_hash'])
