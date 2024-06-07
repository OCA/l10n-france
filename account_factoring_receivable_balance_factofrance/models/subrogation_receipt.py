# © 2024 Open Source Integrators, Daniel Reis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import re

from odoo import _, fields, models, tools
from odoo.exceptions import UserError

FORMAT_VERSION = "7.0"
RETURN = "\r\n"


class SubrogationReceipt(models.Model):
    _inherit = "subrogation.receipt"

    def _prepare_factor_file_factofrance(self):
        "Entry-point to generate the factor file"
        self.ensure_one()
        name = "BPCE_{}_{}_{}.txt".format(  # TODO!
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
        body, max_row, balance = self._get_factofrance_body()
        header = self._get_factofrance_header()
        check_column_size(header)
        ender = self._get_factofrance_ender(max_row, balance)
        check_column_size(ender)
        raw_data = f"{header}{RETURN}{body}{RETURN}{ender}{RETURN}".replace(
            "False", "    "
        )
        data = clean_string(raw_data)
        # check there is no regression in columns position
        check_column_position(raw_data, self.factor_journal_id, False)
        check_column_position(data, self.factor_journal_id)
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
            "code": pad(self.company_id.bpce_factor_code, 6, 0),
            "devise": self.factor_journal_id.currency_id.name,
            "name": pad(self.company_id.partner_id.name, 25),
            "statem_date": bpce_date(self.statement_date),
            "date": bpce_date(self.date),
            "idfile": pad(self.id, 3, 0),
            "reserved": pad(" ", 208),
            "format": FORMAT_VERSION,
        }
        string = "01000001138{code}{devise}{name}{statem_date}{date}"
        string += "{idfile}{format}{reserved}"
        return string.format(**info)

    def _get_factofrance_ender(self, max_row, balance):
        self = self.sudo()
        info = {
            "seq": pad(max_row + 2, 6, 0),
            "code": pad(self.company_id.bpce_factor_code, 6, 0),
            "name": pad(self.company_id.partner_id.name[:25], 25),
            "balance": pad(round(balance * 100), 13, 0),
            "reserved": pad(" ", 220),
        }
        return "09{seq}138{code}{name}{balance}{reserved}".format(**info)

    def _get_factofrance_body(self):
        self = self.sudo()
        sequence = 1
        rows = []
        balance = 0
        for line in self.line_ids:
            move = line.move_id
            partner = line.move_id.partner_id.commercial_partner_id
            if not partner:
                raise UserError(f"Pas de partenaire sur la pièce {line.move_id}")
            sequence += 1
            name = pad(move.name, 30, position="left")
            p_type = get_type_piece(move)
            total = move.amount_total_in_currency_signed
            info = {
                "seq": pad(sequence, 6, 0),
                "siret": pad(" ", 14)
                if not partner.siret
                else pad(partner.siret, 14, 0, position="left"),
                "pname": pad(partner.name[:15], 15, position="left"),
                "ref_cli": pad(partner.ref, 10, position="left"),
                "res1": pad(" ", 5),
                "activity": "D"
                if partner.country_id == self.env.ref("base.fr")
                else "E",
                "res2": pad(" ", 9),
                "cmt": pad(" ", 20),
                "piece": name,
                "piece_factor": get_piece_factor(name, p_type),
                "type": p_type,
                "paym": "VIR"
                if p_type == "FAC"
                else "   ",  # TODO only VIR is implemented
                "date": bpce_date(move.invoice_date if p_type == "FAC" else move.date),
                "date_due": bpce_date(move.invoice_date_due) or pad(" ", 8),
                "total": pad(round(abs(total) * 100), 13, 0),
                "devise": move.currency_id.name,
                "res3": "  ",
                "eff_non_echu": " ",  # TODO
                "eff_num": pad(" ", 7),  # TODO
                "eff_total": pad("", 13, 0),  # effet total TODO not implemented
                "eff_imputed": pad("", 13, 0),  # effet imputé TODO not implemented
                "rib": pad(" ", 23),  # TODO
                "eff_echeance": pad(" ", 8),  # date effet echeance TODO not implemented
                "eff_pull": pad(" ", 10),  # reférence tiré/le nom TODO not implemented
                # 0: traite non accepté, 1: traite accepté, 2: BOR TODO not implemented
                "eff_type": " ",
                "res4": pad(" ", 17),
            }
            balance += total
            fstring = "02{seq}{siret}{pname}{ref_cli}{res1}{activity}{res2}{cmt}"
            fstring += "{piece}{piece_factor}{type}{paym}{date}{date_due}"
            fstring += "{total}{devise}{res3}{eff_non_echu}{eff_num}{eff_total}"
            fstring += "{eff_imputed}{rib}{eff_echeance}{eff_pull}{eff_type}{res4}"
            string = fstring.format(**info)
            check_column_size(string, fstring, info)
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
