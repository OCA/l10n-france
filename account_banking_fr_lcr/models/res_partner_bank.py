# Copyright 2024 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models
from odoo.exceptions import UserError


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    def _fr_iban_validate(self):
        self.ensure_one()
        if self.acc_type != "iban":
            raise UserError(
                _(
                    "Bills of exchange can only use IBAN bank accounts. "
                    "Bank account '%(acc_number)s' of partner '%(partner)s' "
                    "is not an IBAN."
                )
                % {
                    "acc_number": self.acc_number,
                    "partner": self.partner_id.display_name,
                }
            )
        if not self.sanitized_acc_number.startswith("FR"):
            raise UserError(
                _(
                    "Bills of exchange can only use French bank accounts. "
                    "The IBAN '%(acc_number)s' of partner '%(partner)s' "
                    "is not a French IBAN."
                )
                % {
                    "acc_number": self.acc_number,
                    "partner": self.partner_id.display_name,
                }
            )
        assert (
            len(self.sanitized_acc_number) == 27
        ), "French IBANs must have 27 caracters"

    def _fr_iban2rib(self):
        self._fr_iban_validate()
        acc_number = self.sanitized_acc_number
        return {
            "bank": acc_number[4:9],  # code banque
            "branch": acc_number[9:14],  # code guichet
            "account": acc_number[14:25],  # numéro de compte
            "key": acc_number[25:27],  # clé RIB
        }
