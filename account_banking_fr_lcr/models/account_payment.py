# Copyright 2014-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

from .account_payment_order import LCR_DATE_FORMAT

LCR_TYPE_CODES = {
    "not_accepted": "0",
    "accepted": "1",
    "promissory_note": "2",
}


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _prepare_cfonb_line(self, transactions_count):
        """Generate each debit line of the CFONB file"""
        # I use French variable names because the specs are in French
        self.ensure_one()
        order = self.payment_order_id
        payment_line = self.payment_line_ids[0]
        assert order
        code_enregistrement = "06"
        code_operation = "60"
        numero_enregistrement = str(transactions_count + 1).zfill(8)
        reference_tire = order._prepare_lcr_field(
            "Référence tiré", self.payment_reference, 10, reference=True
        )
        rib = self.partner_bank_id._fr_iban2rib()

        nom_tire = order._prepare_lcr_field("Nom tiré", self.partner_id.name, 24)
        if self.partner_bank_id.bank_id:
            nom_banque = order._prepare_lcr_field(
                "Nom banque", self.partner_bank_id.bank_id.name, 24
            )
        else:
            nom_banque = " " * 24
        code_acceptation = LCR_TYPE_CODES[order.payment_method_line_id.fr_lcr_type]
        montant_centimes = str(round(self.amount * 100))
        zero_montant_centimes = montant_centimes.zfill(12)
        if payment_line.move_line_id and payment_line.move_line_id.move_id.invoice_date:
            date_creation_dt = payment_line.move_line_id.move_id.invoice_date
        else:
            date_creation_dt = fields.Date.context_today(self)
        date_creation = date_creation_dt.strftime(LCR_DATE_FORMAT)
        date_echeance = self.date.strftime(LCR_DATE_FORMAT)
        if hasattr(self.partner_id, "siren") and self.partner_id.siren:
            siren_tire = self.partner_id.siren
        else:
            siren_tire = " " * 9
        # I can't use self.name because payment.state == 'draft' so self.name = '/'
        reference_tireur = order._prepare_lcr_field(
            "Référence tireur", payment_line.name, 10, reference=True
        )

        cfonb_line = "".join(
            [
                code_enregistrement,
                code_operation,
                numero_enregistrement,
                " " * (6 + 2),
                reference_tire,
                nom_tire,
                nom_banque,
                code_acceptation,
                " " * 2,
                rib["bank"],
                rib["branch"],
                rib["account"],
                zero_montant_centimes,
                " " * 4,
                date_echeance,
                date_creation,
                " " * (4 + 1 + 3 + 3),
                siren_tire,
                reference_tireur,
            ]
        )
        assert len(cfonb_line) == 160, "LCR CFONB line must have 160 chars"
        return cfonb_line
