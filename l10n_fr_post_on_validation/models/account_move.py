# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.multi
    def post(self, invoice=False):
        # This is stupid, but better to override a 200 line function without
        # calling super to remove one line
        if 'no_post' not in self.env.context:
            return super().post(invoice)
        return

    @api.multi
    def button_cancel(self):
        return super(
            AccountMove, self.filtered(lambda x: x.state != 'draft')
        ).button_cancel()
