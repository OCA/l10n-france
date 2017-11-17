# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, models


class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = ['pos.order', 'certification.model.mixin']

    # Section - Overwrite
    _secured_field_name_list = [
        'date_order', 'session_id', 'company_id', 'partner_id',
        'amount_total', 'amount_tax']

    _secured_line_field_name = 'lines'

    _sequence_holder_field_name = 'session_id.config_id'

    _locked_state_list = ['paid', 'done', 'invoiced']

    @api.multi
    def _get_sequence_holder(self):
        self.ensure_one()
        return self.session_id.config_id

    # Section - Overload
    @api.multi
    def write(self, vals):
        self.check_write_allowed(vals)
        res = super(PosOrder, self).write(vals)
        return res

    @api.multi
    def action_paid(self):
        res = super(PosOrder, self).action_paid()
        self.generate_hash()
        return res

    @api.multi
    def get_certification_information(self):
        """This function is made to allow overload for custom module
        like 'pos_order_load'"""
        return self.read(['pos_reference', 'l10n_fr_hash'])
