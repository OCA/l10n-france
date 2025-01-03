# Copyright 2017-2020 Akretion France (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, fields, models

logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_chorus_api = fields.Boolean(
        string="Use Chorus Pro API",
        implied_group="l10n_fr_chorus_account.group_chorus_api",
        help="If you select 'Use Chorus Pro API', it will add all users to the "
        "Chorus API group.",
    )
    fr_chorus_api_login = fields.Char(
        related="company_id.fr_chorus_api_login", readonly=False
    )
    fr_chorus_api_password = fields.Char(
        related="company_id.fr_chorus_api_password", readonly=False
    )
    fr_chorus_qualif = fields.Boolean(
        string="Use Chorus Qualification Platform",
        readonly=True,
        default=lambda self: self.env.company._chorus_qualif(),
    )
    fr_chorus_invoice_format = fields.Selection(
        related="company_id.fr_chorus_invoice_format", readonly=False
    )
    fr_chorus_check_commitment_number = fields.Boolean(
        related="company_id.fr_chorus_check_commitment_number", readonly=False
    )
    fr_chorus_pwd_expiry_date = fields.Date(
        related="company_id.fr_chorus_pwd_expiry_date", readonly=False
    )
    fr_chorus_expiry_remind_user_ids = fields.Many2many(
        related="company_id.fr_chorus_expiry_remind_user_ids", readonly=False
    )

    def fr_chorus_test_api(self):
        self.ensure_one()
        # The code will raise UserError if the test fails
        logger.info("Start test Chorus Pro API for company %s", self.company_id.name)
        api_params = self.company_id._chorus_get_api_params(raise_if_ko=True)
        url_path = "structures/v1/rechercher"
        payload = {"structure": {"nomStructure": "This is just a test"}}
        answer, session = self.env["res.company"]._chorus_post(
            api_params, url_path, payload
        )
        message = _(
            "Successful test of the Chorus Pro API for company '%(company)s'!",
            company=self.company_id.display_name,
        )
        logger.info(message)
        action = {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }
        return action
