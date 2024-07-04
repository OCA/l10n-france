# © 2024 Open Source Integrators, Daniel Reis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
import re

from odoo import Command, _, api, fields, models
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
        [("101_102", "Only 101-102"), ("103_104", "Only 103-104"), ("both", "Both")]
    )

    @api.onchange("file_type")
    def onchange_file_type(self):
        self.line_ids = self.item_ids = [(6, 0, [])]

    @api.model
    def _get_domain_for_factor(self, factor_type, factor_journal, currency=None):
        domain = super()._get_domain_for_factor(factor_type, factor_journal, currency)
        # TODO: Improve with ref.
        updated_domain = [
            # Also include the related expenses if payment was under the total amount
            ("payment_id", "=", False),
        ]
        return domain + updated_domain

    def _prepare_factor_file_factofrance(self):
        "Entry-point to generate the factor file"
        self.ensure_one()
        name = "F{}_{}_{}.txt".format(  # TODO!
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
        self.env["ir.attachment"].search(
            [("res_id", "in", self.ids), ("res_model", "=", self._name)]
        ).unlink()

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
        # check_column_size(header)

        rows, totals = self._prepare_factofrance_body()
        body = self._get_factofrance_body(rows)
        ender = self._get_factofrance_ender(totals)
        self.balance = totals["balance"]
        # check_column_size(ender)
        raw_data = RETURN.join([header, body, ender])
        data = clean_string(raw_data)
        # non ascii chars are replaced
        data = bytes(data, "ascii", "replace").replace(b"?", b" ")
        return base64.b64encode(data)

    def _get_factofrance_header(self):
        self = self.sudo()

        factor_code = str(self.factor_journal_id.factor_code).ljust(4, " ")
        company_name = self.company_id.name.ljust(40, " ")
        confirm_date = factofrance_date(self.date)
        identification_type = "1"
        country_codes = "2"
        company_identifiers = get_column(
            self.company_id.siret or self.company_id.vat, 14
        )
        file_sequence_number = ("000" + self.name)[-3:]
        currency = self.company_id.currency_id.name.ljust(3, " ")
        operation_type = "000000".ljust(6, " ")

        # Create a list with the header parts, initially filled with spaces
        header_parts = [" "] * 360
        header_parts[0:2] = "100"
        header_parts[3:7] = factor_code  # Position 4 to 7 (not inclusive)
        header_parts[9:49] = company_name  # Position 10 to 49
        header_parts[49:56] = confirm_date  # Position 50 to 56
        header_parts[117] = identification_type  # Position 118
        header_parts[118] = country_codes  # Position 119
        header_parts[119:133] = company_identifiers  # Position 120 to 133
        header_parts[135:137] = file_sequence_number  # Position 136 to 139
        header_parts[351:353] = currency  # Position 352 to 354
        header_parts[354:360] = operation_type  # Position 355 to 360

        # Join the list into a single string
        header = "".join(header_parts)
        return header

    def _get_factofrance_ender(self, totals):
        info = {
            "code": "199",
            "factor_code": str(self.factor_journal_id.factor_code),
            "company_name": self.company_id.name,
            "confirm_date": factofrance_date(self.date),
            "currency": self.company_id.currency_id.name,
            "operation_type": "000000",
        }
        end_parts = [" "] * 360
        end_parts[0:2] = info.get("code")
        end_parts[3:8] = info.get("factor_code")
        end_parts[9:49] = info.get("company_name")
        end_parts[49:56] = info.get("confirm_date")
        end_parts[57:60] = get_column(totals["number_of_invoices"], 4)
        end_parts[61:75] = get_column(totals["total_amount_of_invoices"], 15)
        end_parts[76:79] = get_column(totals["number_of_credit_notes"], 4)
        end_parts[80:94] = get_column(totals["total_amount_of_credit_notes"], 15)
        end_parts[95:98] = get_column(totals["number_of_payments"], 4)
        end_parts[99:113] = get_column(totals["total_amount_of_payments"], 15)
        end_parts[351:353] = info.get("currency")
        end_parts[354:357] = info.get("operation_type")
        # Join the list into a single string
        end = "".join(end_parts)

        return end

    def get_code(self, move, line):
        code = ""
        if move.move_type == "out_invoice":
            code = "101"
        elif move.move_type == "out_refund":
            code = "102"
        elif move.move_type == "entry":
            code = "103"
            if line.account_id.account_type == "expense":
                code = "104"
        return code

    def action_compute_lines(self):
        res = super().action_compute_lines()
        if self.file_type != "101_102":
            if self.file_type != "both":
                self.item_ids.write({"subrogation_id": False})
                self.line_ids = self.item_ids = [(6, 0, [])]

            amls = self.env["account.move.line"].search(
                [
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
            )
            # Exclude lines with credit in bank journal
            amls = amls.filtered(
                lambda aml: aml.journal_id.type != "bank" or aml.credit == 0
            )
            self.write({"item_ids": [Command.link(aml.id) for aml in amls]})
            amls.write({"subrogation_id": self.id})
        return res

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
        for line in self.item_ids:
            move = line.move_id
            partner = line.move_id.partner_id.commercial_partner_id
            if not partner:
                raise UserError(f"Pas de partenaire sur la pièce {line.move_id}")

            code = self.get_code(move, line)
            amount = line.debit or line.credit
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

            info = {
                "code": code or " ",
                "confirm_date": factofrance_date(self.date),
                "factor_code": str(self.factor_journal_id.factor_code) or " ",
                "document": partner.siret or partner.vat or "0",
                "document2": " ",
                "customer_name": (partner.name or " ").ljust(40, " "),
                "customer_address": " ".join(
                    x for x in [partner.street, partner.street2, partner.street3] if x
                ),
                # "customer_street": partner.street
                # and partner.street.ljust(40, " ")
                # or " ",
                # "customer_street2": partner.street2
                # and partner.street2.ljust(40, " ")
                # or "".ljust(40, " "),
                "customer_zip_code": partner.zip or " ",
                "delivery_office": partner.city or " ",
                "customer_country_code": partner.country_id.code or " ",
                "customer_phone": partner.mobile or partner.phone or " ",
                "customer_ref": partner.ref
                and partner.ref.ljust(10, " ")
                or "".ljust(10, " "),
                "date": factofrance_date(move.invoice_date or move.date),
                "number": get_column(move.name.replace("/", ""), 15),
                "currency": self.company_id.currency_id.name or " ",
                "account_sign": "+" if move.move_type == "out_invoice" else "-",
                "amount": (str(amount).replace(".", "")).rjust(15, "0") or " ",
                "payment_mode": "VIR",
                "invoice_date_due": factofrance_date(move.invoice_date_due)
                if move.move_type == "out_invoice"
                else "".ljust(11, " ") or " ",
                "customer_order_reference": move.ref
                and move.ref.ljust(40, " ")
                or "".ljust(40, " "),
                "operation_type": get_type_piece(move, line) or " ",
            }
            rows.append(info)
        return rows, totals

    def _get_factofrance_body(self, rows_info):
        rows = []
        for info in rows_info:
            line = [" "] * 361
            line[0:2] = info.get("code")
            line[3:10] = factofrance_date(self.date)
            line[11:16] = info.get("factor_code")
            line[17:25] = info.get("document")
            line[26:30] = info.get("document2")
            line[31:70] = info.get("customer_name")
            line[111:190] = info.get("customer_address")
            # line[111:150] = info.get("customer_street")
            # line[151:190] = info.get("customer_street2")
            line[191:196] = info.get("customer_zip_code")
            line[197:230] = info.get("delivery_office")
            line[231:233] = info.get("customer_country_code")
            line[234:243] = info.get("customer_phone")[:10]
            line[244:253] = info.get("customer_ref")
            line[254:261] = info.get("date")
            line[262:276] = info.get("number")
            line[277:279] = info.get("currency")
            line[280:280] = info.get("account_sign")
            line[281:295] = info.get("amount")
            line[296:298] = info.get("payment_mode")
            line[299:306] = info.get("invoice_date_due")
            line[307:316] = info.get("customer_order_reference")
            line[357:360] = info.get("operation_type")

            formatted_string = "".join(line)
            rows.append(formatted_string)
        return RETURN.join(rows)


def get_type_piece(move, line):
    p_type = "  "
    move_type = move.move_type
    if move_type == "entry":
        p_type = "VIR"
        if line.account_id.account_type == "expense":
            p_type = "AJC"
    elif move_type == "out_invoice":
        p_type = "FAC"
    elif move_type == "out_refund":
        p_type = "AVO"
    assert len(p_type) == 3
    return p_type


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
        res = str(value).ljust(size, " ")
        res = res[:size]
    return res


def factofrance_date(date_value):
    return date_value.strftime("%Y%m%d") if date_value else " "


def clean_string(string):
    """Remove all except [A-Z], space, \r, \n
    https://www.rapidtables.com/code/text/ascii-table.html"""
    string = string.upper()
    string = re.sub(r"[\x21-\x2F]|[\x3A-\x40]|[\x5E-\x7F]|\x0A\x0D", r" ", string)
    string = string.replace("False", "    ")
    return string


# def check_column_size(string, fstring=None, info=None):
#     print("\n string", string)
#     if len(string) != 358:
#         if fstring and info:
#             fstring = fstring.replace("{", "|{")
#             fstring = fstring.format(**info)
#             strings = fstring.split("|")
#             for mystr in strings:
#                 strings[strings.index(mystr)] = f"{mystr}({len(mystr)})"
#             fstring = "|".join(strings)
#         else:
#             fstring = ""
#         # pylint: disable=C8107
#         raise UserError(
#             "La ligne suivante contient {} caractères au lieu de 275\n\n{}"
#             "\n\nDebugging string:\n{}s".format(len(string), string, fstring)
#         )


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
