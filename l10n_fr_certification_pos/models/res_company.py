# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.multi
    def write(self, vals):
        """Create PoS Config Sequence, if the new setting is requiring one"""
        config_obj = self.env['pos.config']
        res = super(ResCompany, self).write(vals)
        if vals.get('country_id', False):
            for company in self:
                pos_configs = config_obj.search(
                    [('company_id', '=', company.id)])
                pos_configs.generate_secure_sequence_if_required()
        return res
