# © 2024 Open Source Integrators, Daniel Reis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import re

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError

FORMAT_VERSION = "7.0"
RETURN = "\r\n"


class SubrogationReceipt(models.Model):
    _inherit = "subrogation.receipt"

    @api.model
    def _get_domain_for_factor(self, factor_type, factor_journal, currency=None):
        domain = super(SubrogationReceipt, self)._get_domain_for_factor(
            factor_type, factor_journal, currency
        )
        # TODO: Improve with ref.
        updated_domain = [
            # From an eligible customer
            ("partner_id.factor_journal_id", "=", factor_journal.id),
            ("journal_id.type", "=", "sale"),
            ("journal_id.is_factor_sale_journal", "=", True),
            # Pay and invoice previously sent fr factoring
            ("subrogation_id", "=", False),
            # Also include the related expenses if payment was under the total amount
            ("payment_id", "=", False),
        ]
        return domain + updated_domain

    def _prepare_factor_file_factofrance(self):
        "Entry-point to generate the factor file"
        self.ensure_one()
        name = "F{}_{}_{}.txt".format(  # TODO!
            self._sanitize_filepath(f"{fields.Date.today()}"),
            self.id,
            self._sanitize_filepath(self.company_id.name),
        )
        return {
            "name": name,
            "res_id": self.id,
            "res_model": self._name,
            "datas": self._prepare_factor_file_data_factofrance(),
        }

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

        body, max_row, balance = self._get_factofrance_body()
        # 5 / 0
        ender = self._get_factofrance_ender(max_row, balance)
        # check_column_size(ender)
        raw_data = f"{header}{RETURN}{body}{RETURN}{ender}{RETURN}".replace(
            "False", "    "
        )
        data = clean_string(raw_data)
        # check there is no regression in columns position
        # check_column_position(raw_data, self.factor_journal_id, False)
        # check_column_position(data, self.factor_journal_id)
        dev_mode = tools.config.options.get("dev_mode")
        if dev_mode and dev_mode[0][-3:] == "pdb" or False:
            # make debugging easier saving file on filesystem to check
            debug(raw_data, "_raw")
            debug(data)
            # pylint: disable=C8107
            raise UserError("See files /odoo/subrog*.txt")
        total_in_erp = sum(self.line_ids.mapped("amount_currency"))
        if round(balance, 2) != round(total_in_erp, 2):
            # pylint: disable=C8107
            raise UserError(
                "Erreur dans le calul de la balance :"
                f"\n - erp : {total_in_erp}\n - fichier : {balance}"
            )
        self.write({"balance": balance})
        # non ascii chars are replaced
        data = bytes(data, "ascii", "replace").replace(b"?", b" ")
        return base64.b64encode(data)

    def _get_factofrance_header(self):
        self = self.sudo()
        info = {
            "factor_code": pad(self.factor_journal_id.factor_code, 4),
            "company_name": pad(self.company_id.name, 10),
            "create_date": pad(factofrance_date(self.create_date), 50),
            "identification_type": pad("1", 118),
            "country_codes": pad("2", 119, " "),
            "company_identifiers": pad(
                self.company_id.siret or self.company_id.vat, 120, " "
            ),
            "file_sequence_number": pad(self.id, 136, " "),
            "currency": pad(self.company_id.currency_id.name, 352, " "),
            "operation_type": pad("000000", 355, " "),
        }
        string = "100{factor_code}{company_name}{create_date}{identification_type}{country_codes}"
        string += (
            "{company_identifiers}{file_sequence_number}{currency}{operation_type}"
        )
        return string.format(**info)

    def _get_factofrance_ender(self, max_row, balance):
        self = self.sudo()
        invoices = self.item_ids.filtered(
            lambda line: not line.is_refund
            and line.move_id.move_type in ("out_invoice")
        )
        credit_notes = self.item_ids.filtered(
            lambda line: line.is_refund and line.move_id.move_type in ("out_refund")
        )
        info = {
            "code": pad("199", 1),
            "factor_code": pad(self.factor_journal_id.factor_code, 4, " "),
            "company_name": pad(self.company_id.name, 10, " "),
            "create_date": pad(factofrance_date(self.create_date), 50, " "),
            "number_of_invoices": pad(len(invoices.mapped("move_id")), 58, " "),
            # "total_amount_of_invoices": pad(sum(invoices.mapped("move_id.amount_total")), ),
            # "number_of_credit_notes": len(credit_notes.mapped("move_id")),
            # "total_amount_of_credit_notes": sum(
            # credit_notes.mapped("move_id.amount_total")
            # ),
            # "number_of_payments": len(self.item_ids.mapped("move_id")),
            # "total_amount_of_payments": sum(
            # self.item_ids.mapped("move_id.amount_total")
            # ),
            # "currency": self.company_id.currency_id.name,
            "operation_type": pad("000000", 355, " "),
        }
        string = "{code}{factor_code}{company_name}{create_date}{number_of_invoices}{operation_type}"
        return string.format(**info)

    def get_code(self, move):
        if move.move_type == "out_invoice":
            code = "101"
        elif move.move_type == "out_refund":
            code = "102"
        # elif move.move_type == ''
        return code

    def _get_factofrance_body(self):
        self = self.sudo()
        rows = []
        balance = 0
        for line in self.line_ids:
            move = line.move_id
            partner = line.move_id.partner_id.commercial_partner_id
            if not partner:
                raise UserError(f"Pas de partenaire sur la pièce {line.move_id}")
            total = move.amount_total_in_currency_signed
            info = {
                "code": pad(self.get_code(move), 1, " "),
                "create_date": pad(factofrance_date(move.create_date), 4, " "),
                "factor_code": pad(self.factor_journal_id.factor_code, 12, " "),
                "company_identifiers": pad(
                    self.company_id.siret or self.company_id.vat, 18, " "
                ),
                "document": pad("siret" if partner.siret else "vat", 18, " "),
                "document2": pad("", 27, " "),
                "customer_name": pad(partner.name, 32, " "),
                "customer_street": pad(partner.street, 112, " "),
                "customer_street2": pad(partner.street2, 152, " "),
                "customer_zip_code": pad(partner.zip, 192, " "),
                "delivery_office": pad("", 198, " "),
                "customer_country_code": pad(partner.country_id.code, 232, " "),
                "customer_phone": pad(partner.mobile or partner.phone, 235, " "),
                "customer_ref": pad(partner.ref, 245, " "),
                "date": pad(factofrance_date(move.invoice_date or move.date), 255, " "),
                "number": pad(move.name, 263, " "),
                "currency": pad(self.company_id.currency_id.name, 278, " "),
                # "amount_sign": pad(move.amount_total_signed, ), # TODO
                "amount": pad(move.amount_total, 282, " "),
                # "payment_mode":
                # "invoice_due_date": factofrance_date(move.invoice_date_due),
                "customer_order_reference": pad(move.ref, 308, " "),
                # "journal_code":
                "operation_type": get_type_piece(move),
            }
            balance += total
            fstring = "{code}{create_date}{company_identifiers}{document}{document2}{customer_name}{customer_street}"
            fstring += "{customer_zip_code}{delivery_office}{customer_country_code}{customer_phone}{customer_ref}{date}"
            fstring += (
                "{number}{currency}{amount}{customer_order_reference}{operation_type}"
            )
            string = fstring.format(**info)
            # check_column_size(string, fstring, info)
            rows.append(string)
        return (RETURN.join(rows), len(rows), balance)


def get_piece_factor(name, p_type):
    if not p_type:
        return "{}{}".format(name[:15], pad(" ", 15))
    return name[:30]


def get_type_piece(move):
    journal_type = move.journal_id.type
    p_type = False
    move_type = move.move_type
    if move_type == "entry":
        if journal_type == "general":
            # TODO : improve
            od_type = False
            lines = move.line_ids.filtered(
                lambda s: s.account_id.group_id == s.env.ref("l10n_fr.1_pcg_411")
            )
            for line in lines:
                if max(line.debit, line.credit) == move.amount_total:
                    if line.debit == move.amount_total:
                        od_type = "D"
                    else:
                        od_type = "C"
                    break
            if not od_type:
                # pylint: disable=C8107
                raise UserError(f"Impossible de déterminer le type de l'OD {move.name}")
            p_type = f"OD{od_type}"
    elif move_type == "out_invoice":
        p_type = "FAC"
    elif move_type == "out_refund":
        p_type = "AVO"
    assert len(p_type) == 3
    return p_type


def factofrance_date(date_field):
    return date_field.strftime("%Y%m%d")


def bpce_date(date_field):
    return date_field.strftime("%d%m%Y")


def pad(string, pad, end=" ", position="right"):
    "Complete string by leading `end` string from `position`"
    if isinstance(end, int | float):
        end = str(end)
    if isinstance(string, int | float):
        string = str(string)
    if position == "right":
        string = string.rjust(pad, end)
    else:
        string = string.ljust(pad, end)
    return string


def clean_string(string):
    """Remove all except [A-Z], space, \r, \n
    https://www.rapidtables.com/code/text/ascii-table.html"""
    string = string.replace(FORMAT_VERSION, "FORMATVERSION")
    string = string.upper()
    string = re.sub(r"[\x21-\x2F]|[\x3A-\x40]|[\x5E-\x7F]|\x0A\x0D", r" ", string)
    string = string.replace("FORMATVERSION", FORMAT_VERSION)
    return string


def debug(content, suffix=""):
    mpath = f"/odoo/subrog{suffix}.txt"
    with open(mpath, "wb") as f:
        if isinstance(content, str):
            content = bytes(content, "ascii", "replace")
        f.write(content)


def check_column_size(string, fstring=None, info=None):
    print("\n string", string)
    if len(string) != 275:
        if fstring and info:
            fstring = fstring.replace("{", "|{")
            fstring = fstring.format(**info)
            strings = fstring.split("|")
            for mystr in strings:
                strings[strings.index(mystr)] = f"{mystr}({len(mystr)})"
            fstring = "|".join(strings)
        else:
            fstring = ""
        # pylint: disable=C8107
        raise UserError(
            "La ligne suivante contient {} caractères au lieu de 275\n\n{}"
            "\n\nDebugging string:\n{}s".format(len(string), string, fstring)
        )


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
