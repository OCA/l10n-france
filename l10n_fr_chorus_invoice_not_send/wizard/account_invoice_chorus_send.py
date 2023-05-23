# Copyright 2023 Akretion France (http://www.akretion.com/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountInvoiceChorusSend(models.TransientModel):
    _inherit = "account.invoice.chorus.send"

    def run(self):
        super().run()
        return
