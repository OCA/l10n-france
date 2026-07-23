# © 2024 Open Source Integrators, Daniel Reis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
import re

from unidecode import unidecode

from odoo import _, api, fields, models
from odoo.exceptions import UserError

RETURN = "\r\n"


class SubrogationReceipt(models.Model):
    _inherit = "subrogation.receipt"

    name = fields.Char(
        required=True,
        copy=False,
        readonly=False,
        default=lambda self: _("New"),
    )
    file_type = fields.Selection(
        [
            ("101_102", _("Remise de factures")),
            ("103_104", _("Lettrages")),
            ("both", _("Remise de factures et lettrages")),
        ]
    )

    @api.model
    def _get_domain_for_factor(self):
        domain = super()._get_domain_for_factor()
        # Also include the related expenses if payment was under the total amount
        updated_domain = [("payment_id", "=", False)]
        return domain + updated_domain

    def _prepare_factor_file_factofrance(self):
        "Entry-point to generate the factor file"
        self.ensure_one()
        name = "F{}_{}_{}.txt".format(
            self._sanitize_filepath(self.name),
            self._sanitize_filepath(
                dict(self._fields["file_type"].selection).get(self.file_type)
            ),
            self._sanitize_filepath(f"{fields.Date.today()}"),
        )
        return {
            "name": name,
            "res_id": self.id,
            "res_model": self._name,
            "datas": self._prepare_factor_file_data_factofrance(),
        }

    def action_confirm(self):
        for rec in self:
            if rec.name == _("New"):
                rec.name = self.env["ir.sequence"].next_by_code("factoring.receivable")
        res = super().action_confirm()
        self.write({"state": "posted"})
        return res

    def action_draft(self):
        self.write({"state": "draft"})

    def _prepare_factor_file_data_factofrance(self):
        self.ensure_one()
        if not self.factor_journal_id.factor_code:
            msg = _(
                "Le code du factor n'est pas renseigné dans l'onglet 'Factor'.\n"
                "Vous devez mettre le code du factor dans la société '{}'.\n"
                "Champ dans l'onglet 'Factor'",
                self.env.company.name,
            )
            raise UserError(msg)
        if not self.statement_date:
            raise UserError(_("Vous devez spécifier la date du dernier relevé"))

        header = self._get_factofrance_header()
        rows, totals = self._prepare_factofrance_body()
        body = self._get_factofrance_body(rows)
        ender = self._get_factofrance_ender(totals)
        self.balance = totals["balance"]
        raw_data = RETURN.join([header, body, ender]) + RETURN
        ansi_data = raw_data.encode("latin-1")
        return base64.b64encode(ansi_data)

    def _get_factofrance_header(self):
        factor_code = self.factor_journal_id.factor_code
        company_name = self.company_id.name
        confirm_date = factofrance_date(self.date)
        identification_type = self.factor_journal_id.partner_identification_type or "1"
        country_codes = "2"
        company_identifiers = self.company_id.siret or self.company_id.vat
        file_sequence_number = ("000" + self.name)[-3:]
        currency = self.company_id.currency_id.name
        operation_type = "000000"

        # Create a list with the header parts, initially filled with spaces
        header = " " * 360
        header = set_column(header, 1, 3, "100")
        header = set_column(header, 4, 6, factor_code)
        header = set_column(header, 10, 40, company_name)
        header = set_column(header, 50, 8, confirm_date)
        header = set_column(header, 118, 1, identification_type)
        header = set_column(header, 119, 1, country_codes)
        header = set_column(header, 120, 16, company_identifiers)
        header = set_column(header, 136, 3, file_sequence_number)
        header = set_column(header, 352, 3, currency)
        header = set_column(header, 355, 6, operation_type)
        return header

    def _get_factofrance_ender(self, totals):
        factor_code = str(self.factor_journal_id.factor_code)
        company_name = self.company_id.name
        confirm_date = factofrance_date(self.date)
        currency = self.company_id.currency_id.name
        operation_type = "000000"

        end = " " * 360
        end = set_column(end, 1, 3, "199")
        end = set_column(end, 4, 6, factor_code)
        end = set_column(end, 10, 40, company_name)
        end = set_column(end, 50, 8, confirm_date)
        end = set_column(end, 58, 4, totals["number_of_invoices"])
        end = set_column(end, 62, 15, totals["total_amount_of_invoices"])
        end = set_column(end, 77, 4, totals["number_of_credit_notes"])
        end = set_column(end, 81, 15, totals["total_amount_of_credit_notes"])
        end = set_column(end, 96, 4, totals["number_of_payments"])
        end = set_column(end, 100, 15, totals["total_amount_of_payments"])
        end = set_column(end, 134, 4, totals.get("number_of_garanties", 0))
        end = set_column(end, 138, 15, totals.get("total_amount_of_garantie", 0.0))
        end = set_column(end, 352, 3, currency)
        end = set_column(end, 355, 6, operation_type)
        return end

    def _get_domain_payments(self):
        return [
            ("date", "<=", self.target_date),
            ("parent_state", "=", "posted"),
            ("payment_id", "!=", False),
            (
                "partner_id.commercial_partner_id.factor_journal_id",
                "=",
                self.factor_journal_id.id,
            ),
            ("partner_id.factor_journal_id", "=", self.factor_journal_id.id),
            ("subrogation_id", "=", False),
        ]

    def _get_factor_lines(self):
        lines = super()._get_factor_lines()
        if self.file_type == "103_104":
            lines = self.env["account.move.line"]
        if self.file_type != "101_102":
            domain = self._get_domain_payments()
            amls = self.env["account.move.line"].search(domain)
            # Exclude lines with credit in bank journal
            amls = amls.filtered(
                lambda aml: aml.journal_id.type != "bank" or aml.credit == 0
            )
            lines |= amls
        return lines

    def _get_line_code_type_sign(self, line):
        move = line.move_id
        if move.move_type == "out_invoice":
            code, op_type, sign = "101", "FAC", 1
        elif move.move_type == "out_refund":
            code, op_type, sign = "102", "AVO", 1
        elif line.account_id.account_type.startswith("asset"):
            code, op_type, sign = "103", "VIR", -1
        else:
            code, op_type, sign = "104", "AJC", -1
        return code, op_type, sign

    def _get_line_due_date(self, line, op_type):
        due_date = None
        if op_type in ["FAC", "AVO", "VIR"]:
            due_date = line.date_maturity
        return due_date

    def _prepare_factofrance_body(self):
        rows = []
        totals = {
            "number_of_invoices": 0,
            "total_amount_of_invoices": 0.00,
            "number_of_credit_notes": 0,
            "total_amount_of_credit_notes": 0.00,
            "number_of_payments": 0,
            "total_amount_of_payments": 0.00,
            "balance": 0.00,
        }
        for line in self.line_ids:
            info = self._prepare_factofrance_body_line(line)
            code, amount = info["code"], info["amount_signed"]
            if code == "101":
                totals["number_of_invoices"] += 1
                totals["total_amount_of_invoices"] += amount
            elif code == "102":
                totals["number_of_credit_notes"] += 1
                totals["total_amount_of_credit_notes"] += amount
            elif code == "103":
                totals["number_of_payments"] += 1
                totals["total_amount_of_payments"] += amount
            totals["balance"] += line.balance
            rows.append(info)
        return rows, totals

    def _prepare_factofrance_body_line(self, line):
        move = line.move_id
        journal = self.factor_journal_id
        partner = line.move_id.partner_id.commercial_partner_id
        if not partner:
            raise UserError(f"Pas de partenaire sur la pièce {line.move_id}")

        code, op_type, sign = self._get_line_code_type_sign(line)
        due_date = self._get_line_due_date(line, op_type)
        amount = (line.debit - line.credit) * sign
        identification_type = journal.partner_identification_type
        info = {
            "code": code or " ",
            "confirm_date": factofrance_date(self.date),
            "factor_code": str(journal.factor_code),
            "document": (
                (partner.siret or "0")
                if identification_type == "1"
                else (partner.vat or "0")
            ),
            "customer_name": partner.name or "",
            "customer_address": " ".join(
                x for x in [partner.street, partner.street2, partner.street3] if x
            ),
            # "customer_street": partner.street
            # and partner.street.ljust(40, " ")
            # or " ",
            # "customer_street2": partner.street2
            # and partner.street2.ljust(40, " ")
            # or "".ljust(40, " "),
            "customer_zip_code": partner.zip or "",
            "delivery_office": partner.city or "",
            "customer_country_code": partner.country_id.code or "",
            "customer_phone": (partner.phone or partner.mobile or "").replace(" ", ""),
            "customer_ref": partner.ref or "",
            "date": factofrance_date(move.invoice_date or move.date),
            # For document number, Invoices use payment ref, Payments use the paid ref
            "number": move.payment_reference or move.ref or move.name,
            "currency": self.company_id.currency_id.name or "",
            "account_sign": "-" if amount < 0 else "+",
            "amount_signed": amount,
            "amount": abs(amount),
            "payment_mode": "VIR",
            "date_due": factofrance_date(due_date),
            "customer_order_reference": move.ref or "",
            "operation_type": op_type,
            "move_type": move.move_type,
        }
        return info

    def _get_factofrance_body(self, rows_info):
        rows = []
        for info in rows_info:
            line = " " * 360
            line = set_column(line, 1, 3, info["code"])
            line = set_column(line, 4, 8, factofrance_date(self.date))
            line = set_column(line, 12, 6, info["factor_code"])
            line = set_column(line, 18, 9 + 5, info["document"])
            line = set_column(line, 32, 40, info["customer_name"])
            line = set_column(line, 112, 40 + 40, info["customer_address"])
            line = set_column(line, 192, 6, info["customer_zip_code"])
            line = set_column(line, 198, 34, info["delivery_office"])
            line = set_column(line, 232, 3, info["customer_country_code"])
            line = set_column(line, 235, 10, info["customer_phone"])
            line = set_column(line, 245, 10, info["customer_ref"])
            line = set_column(line, 255, 8, info["date"])
            line = set_column(line, 263, 15, info["number"])
            line = set_column(line, 278, 3, info["currency"])
            line = set_column(line, 281, 1, info["account_sign"], noformat=True)
            line = set_column(line, 282, 15, info["amount"])
            if info["move_type"].startswith("out"):
                line = set_column(line, 297, 3, info["payment_mode"])
                line = set_column(line, 300, 8, info["date_due"])
                line = set_column(line, 308, 10, info["customer_order_reference"])
            else:
                line = set_column(line, 297, 8, info["date_due"])
            line = set_column(line, 358, 3, info["operation_type"])
            rows.append(line)
        return RETURN.join(rows)


def get_column(value, size):
    if isinstance(value, int):
        if value >= pow(10, size):
            res = "9" * size
        else:
            res = str(value or 0).rjust(size, "0")
            res = res[-size:]
    elif isinstance(value, float):
        if value * 100 >= pow(10, size):
            res = "9" * size
        else:
            res = str(round(value * 100) or 0).rjust(size, "0")
            res = res[-size:]
    else:
        res = clean_string(str(value)).ljust(size, " ")
        res = res[:size]
    return res


def set_column(line, position, length, value, noformat=False):
    value_str = value if noformat else get_column(value, length)
    res = line[: position - 1] + value_str + line[position + length - 1 :]
    return res


def factofrance_date(date_value):
    return date_value.strftime("%Y%m%d") if date_value else ""


def clean_string(string):
    """Remove all except [A-Z], space, \r, \n
    https://www.rapidtables.com/code/text/ascii-table.html"""
    string = unidecode(string.upper())
    string = re.sub(r"[\x21-\x2F]|[\x3A-\x40]|[\x5E-\x7F]|\x0A\x0D", r"", string)
    string = string.replace("False", "    ")
    return string


def check_column_position(content, factor_journal, final=True):
    line2 = content.split(RETURN)[1]
    # line2 = content.readline(2)
    currency = line2[177:180]
    msg = "Problème de décalage colonne dans le fichier"
    if final:
        msg += " final"
    else:
        msg += " brut"
    assert currency == factor_journal.currency_id.name, msg
