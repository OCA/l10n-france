# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import Warning as UserError


class AccountMoveLine(models.Model):
    _name = 'account.move.line'
    _inherit = ['account.move.line', 'certification.model.line.mixin']

    # Section - Overwrite
    _secured_field_name_list = [
        'debit', 'credit', 'account_id', 'move_id', 'partner_id']

    _secured_model_field_name = 'move_id'

    # Section - Overload
    @api.multi
    def write(self, vals, check=True, update_check=True):
        self.check_write_allowed(vals)
        res = super(AccountMoveLine, self).write(
            vals, check=check, update_check=update_check)
        return res
