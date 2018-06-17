# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, models


class PosOrderLine(models.Model):
    _name = 'pos.order.line'
    _inherit = ['pos.order.line', 'certification.model.line.mixin']

    # Section - Overwrite
    _secured_field_name_list = [
        'product_id', 'qty', 'price_unit', 'discount', 'price_subtotal',
        'price_subtotal_incl']

    _secured_model_field_name = 'order_id'

    # Section - Overload
    @api.multi
    def write(self, vals, check=True, update_check=True):
        self.check_write_allowed(vals)
        res = super(PosOrderLine, self).write(
            vals, check=check, update_check=update_check)
        return res
