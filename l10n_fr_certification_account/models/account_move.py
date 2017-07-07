# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import Warning as UserError


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'certification.model.mixin']

    # Section - Overwrite
    _secured_field_name_list = ['date', 'journal_id', 'company_id']

    _secured_line_field_name = 'line_id'

    _sequence_holder_field_name = 'company_id'

    _locked_state_list = ['posted']

    @api.multi
    def _get_sequence_holder(self):
        self.ensure_one()
        return self.company_id

    # Section - Overload
    @api.multi
    def write(self, vals):
        self.check_write_allowed(vals)
        res = super(AccountMove, self).write(vals)
        return res

    @api.multi
    def button_cancel(self):
        # We check on the call of cancel, because button_cancel doesn't
        # update state by ORM but by SQL request
        self.check_write_allowed({'state': 'draft'})
        return super(AccountMove, self).button_cancel()

    @api.multi
    def post(self):
        self.generate_hash()
        res = super(AccountMove, self).post()
        return res
