# Copyright 2024 Akretion (https://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import models
from odoo.tools.misc import formatLang


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def get_journal_dashboard_datas(self):
        number_chorus_error = sum_chorus_error = 0
        res = super().get_journal_dashboard_datas()
        if self.type == "sale":
            data = self.env["account.move"].read_group(
                [
                    ("journal_id", "=", self.id),
                    (
                        "activity_type_id",
                        "=",
                        self.env.ref(
                            "l10n_fr_chorus_account.mail_activity_type_chorus_error"
                        ).id,
                    ),
                ],
                ["amount_total_signed"],
                ["journal_id"],
            )
            if data:
                number_chorus_error = data[0]["journal_id_count"]
                currency = self.currency_id or self.company_id.currency_id
                sum_chorus_error = formatLang(
                    self.env,
                    currency.round(data[0]["amount_total_signed"]),
                    currency_obj=currency,
                )
        res.update(
            {
                "number_chorus_error": number_chorus_error,
                "sum_chorus_error": sum_chorus_error,
            }
        )
        return res
