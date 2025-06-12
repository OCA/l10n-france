# Copyright 2014-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date

logger = logging.getLogger(__name__)


try:
    from unidecode import unidecode
except ImportError:
    logger.debug("unidecode lib not installed")
    unidecode = False

LCR_DATE_FORMAT = "%d%m%y"
LCR_TYPE_CODES = {
    "not_accepted": "0",
    "accepted": "1",
    "promissory_note": "2",
}
LCR_COLLECTION_OPTION = {
    "due_date": "3",
    "due_date_fixed_delay": "4",
    "cash_discount": "1",
    "value_cash_discount": "2",
}
LCR_DAILLY_OPTION = {
    "none": "0",
    "cash_discount": "1",
    "debt_pledge": "2",
    "out_of_agreement": "3",
}


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    fr_lcr_collection_option = fields.Selection(
        lambda self: self.env[
            "account.payment.method.line"
        ]._fr_lcr_collection_option_selection(),
        compute="_compute_fr_lcr_fields",
        store=True,
        precompute=True,
        readonly=False,
        string="Collection Option",
    )
    # if fr_lcr_value_date is also used for Dailly, we'll have to change
    # the code and the view
    fr_lcr_value_date = fields.Date(string="Value Date")
    # invisible, to show or not the field 'fr_lcr_dailly_option'
    fr_lcr_dailly = fields.Boolean(
        string="Dailly Convention",
        compute="_compute_fr_lcr_fields",
        store=True,
        precompute=True,
    )
    fr_lcr_dailly_option = fields.Selection(
        lambda self: self.env[
            "account.payment.method.line"
        ]._fr_lcr_dailly_option_selection(),
        compute="_compute_fr_lcr_fields",
        store=True,
        precompute=True,
        readonly=False,
        string="Dailly Option",
    )

    @api.depends("payment_method_line_id")
    def _compute_fr_lcr_fields(self):
        for order in self:
            fr_lcr_collection_option = False
            fr_lcr_dailly = False
            fr_lcr_dailly_option = False
            if order.payment_method_line_id.payment_method_id.code == "fr_lcr":
                method_line = order.payment_method_line_id
                fr_lcr_collection_option = method_line.fr_lcr_default_collection_option
                fr_lcr_dailly = method_line.fr_lcr_dailly
                fr_lcr_dailly_option = method_line.fr_lcr_default_dailly_option
            order.fr_lcr_collection_option = fr_lcr_collection_option
            order.fr_lcr_dailly = fr_lcr_dailly
            order.fr_lcr_dailly_option = fr_lcr_dailly_option

    def draft2open(self):
        # I call super() first to raise error immediately if partner_bank_id is missing
        # so, in my code below, I know that line.partner_bank_id is set
        # Check on payment lines is handled by draft2open_payment_line_check()
        # on account.payment.line
        res = super().draft2open()
        today = fields.Date.context_today(self)
        for order in self:
            if order.payment_method_code == "fr_lcr":
                if not order.fr_lcr_collection_option:
                    raise UserError(
                        _("The Collection Option is not set on debit order '%s'.")
                        % order.display_name
                    )
                if order.fr_lcr_collection_option in (
                    "cash_discount",
                    "value_cash_discount",
                ):
                    if not order.fr_lcr_value_date:
                        raise UserError(
                            _(
                                "Value date is not set on debit order '%s'. It is "
                                "required on letters of exchange with cash discount."
                            )
                            % order.display_name
                        )
                    elif order.fr_lcr_value_date < today:
                        raise UserError(
                            _(
                                "On debit order '%(order)s', the value date has been "
                                "set to %(value_date)s: it must be in the future.",
                                order=order.display_name,
                                value_date=format_date(
                                    self.env, order.fr_lcr_value_date
                                ),
                            )
                        )
        return res

    @api.model
    def _prepare_lcr_field(self, field_name, value, size, reference=False):
        """if reference is True: cut from end (not from start)
        adjust with 0 (instead of space) and only accept letters and digits
        """
        if not value:
            raise UserError(
                _(
                    "Error in the generation of the CFONB file: "
                    "the field '%s' is empty or 0. It should have a non-null value."
                )
                % field_name
            )
        if not isinstance(value, str):
            raise UserError(
                _(
                    "Error in the generation of the CFONB file: "
                    "'%(field)s' should be a string, "
                    "but it is %(value_type)s (value: %(value)s).",
                    field=field_name,
                    value_type=type(value),
                    value=value,
                )
            )
        value = unidecode(value)
        # page 25 of the CFONB specs:
        # allowed chars are a-z, digits and  * ( ) . , / + - : <espace>
        value = value.upper()
        if reference:
            value = re.sub(r"[^A-Z0-9]", "", value)
        else:
            value = re.sub(r"[^A-Z0-9\*\(\)\.,/\+\-:\s]", "-", value)
        # Cut if too long
        if len(value) > size:
            if reference:
                value = value[-size:]  # cut from end
            else:
                value = value[:size]  # cut from start
        # enlarge if too small: add spaces at the end
        elif len(value) < size:
            if reference:
                value = value.rjust(size, "0")
            else:
                value = value.ljust(size, " ")
        assert len(value) == size, "The length of the field is wrong"
        return value

    def _prepare_first_cfonb_line(self):
        """Generate the header line of the CFONB file"""
        self.ensure_one()
        code_enregistrement = "03"
        code_operation = "60"
        numero_enregistrement = "00000001"
        numero_emetteur = "000000"  # It is not needed for LCR
        if self.payment_method_line_id.fr_lcr_convention_type:
            type_convention = self._prepare_lcr_field(
                "Type de convention",
                self.payment_method_line_id.fr_lcr_convention_type,
                6,
            )
        else:
            type_convention = " " * 6
        # this number is only required for old national direct debits
        today_dt = fields.Date.context_today(self)
        date_remise = today_dt.strftime(LCR_DATE_FORMAT)
        raison_sociale_cedant = self._prepare_lcr_field(
            "Raison sociale du cédant", self.company_id.name, 24
        )
        domiciliation_bancaire_cedant = self._prepare_lcr_field(
            "Domiciliation bancaire du cédant",
            self.company_partner_bank_id.bank_id.name,
            24,
        )
        code_entree = LCR_COLLECTION_OPTION[self.fr_lcr_collection_option]
        if self.fr_lcr_dailly and self.fr_lcr_dailly_option:
            code_dailly = LCR_DAILLY_OPTION[self.fr_lcr_dailly_option]
        else:
            code_dailly = " "
        code_monnaie = "E"
        rib = self.company_partner_bank_id._fr_iban2rib()
        ref_remise = self._prepare_lcr_field("Référence de la remise", self.name, 11)
        if self.fr_lcr_collection_option in ("cash_discount", "value_cash_discount"):
            date_de_valeur = self.fr_lcr_value_date.strftime(LCR_DATE_FORMAT)
        else:
            date_de_valeur = " " * 6
        if (
            hasattr(self.company_id.partner_id, "siren")
            and self.company_id.partner_id.siren
        ):
            siren_cedant = self.company_id.partner_id.siren + " " * 6
        else:
            siren_cedant = " " * 15
        cfonb_line = "".join(
            [
                code_enregistrement,
                code_operation,
                numero_enregistrement,
                numero_emetteur,
                type_convention,
                date_remise,
                raison_sociale_cedant,
                domiciliation_bancaire_cedant,
                code_entree,
                code_dailly,
                code_monnaie,
                rib["bank"],
                rib["branch"],
                rib["account"],
                " " * 16,
                date_de_valeur,
                " " * 10,
                siren_cedant,
                # Date de valeur is left empty because it is only for
                # "remise à l'escompte" and we do
                # "Encaissement, crédit forfaitaire après l’échéance"
                ref_remise,
            ]
        )
        assert len(cfonb_line) == 160, "LCR CFONB line must have 160 chars"
        return cfonb_line

    def _prepare_final_cfonb_line(self, total_amount, transactions_count):
        """Generate the last line of the CFONB file"""
        code_enregistrement = "08"
        code_operation = "60"
        numero_enregistrement = str(transactions_count + 2).zfill(8)
        montant_total_centimes = str(round(total_amount * 100))
        zero_montant_total_centimes = montant_total_centimes.zfill(12)
        cfonb_line = "".join(
            [
                code_enregistrement,
                code_operation,
                numero_enregistrement,
                " " * (6 + 12 + 24 + 24 + 1 + 2 + 5 + 5 + 11),
                zero_montant_total_centimes,
                " " * (4 + 6 + 10 + 15 + 5 + 6),
            ]
        )
        assert len(cfonb_line) == 160, "LCR CFONB line must have 160 chars"
        return cfonb_line

    def _fr_lcr_line_separator(self):
        """It seems that some bank don't want a line break. For the moment,
        we have this hook. If it is confirm, we'll make it a configuration parameter
        """
        return "\r\n"

    def generate_payment_file(self):
        """Creates the LCR CFONB file."""
        self.ensure_one()
        if self.payment_method_id.code != "fr_lcr":
            return super().generate_payment_file()

        cfonb_lines = []
        cfonb_lines.append(self._prepare_first_cfonb_line())
        total_amount = 0.0
        transactions_count = 0
        eur_currency_id = self.env.ref("base.EUR").id
        for payment in self.payment_ids:
            assert payment.currency_id.id == eur_currency_id
            transactions_count += 1
            cfonb_lines.append(payment._prepare_cfonb_line(transactions_count))
            total_amount += payment.amount

        cfonb_lines.append(
            self._prepare_final_cfonb_line(total_amount, transactions_count)
        )
        line_separator = self._fr_lcr_line_separator()
        logger.debug("LCR line separator is %s", line_separator)
        cfonb_string = line_separator.join(cfonb_lines)
        cfonb_bytes = cfonb_string.encode("ascii")
        return (cfonb_bytes, "txt")
