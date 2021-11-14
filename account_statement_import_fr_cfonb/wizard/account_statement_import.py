# Copyright 2014-2020 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CFONB_WIDTH = 120


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    _excluded_accounts = []

    def _parse_cfonb_amount(self, amount_str, nb_of_dec):
        """Taken from the cfonb lib"""
        if nb_of_dec:
            amount_str = amount_str[:-nb_of_dec] + "." + amount_str[-nb_of_dec:]
        # translate the last char and set the sign
        credit_trans = {
            "A": "1",
            "B": "2",
            "C": "3",
            "D": "4",
            "E": "5",
            "F": "6",
            "G": "7",
            "H": "8",
            "I": "9",
            "{": "0",
        }
        debit_trans = {
            "J": "1",
            "K": "2",
            "L": "3",
            "M": "4",
            "N": "5",
            "O": "6",
            "P": "7",
            "Q": "8",
            "R": "9",
            "}": "0",
        }
        assert (
            amount_str[-1] in debit_trans or amount_str[-1] in credit_trans
        ), "Invalid amount in CFONB file"
        if amount_str[-1] in debit_trans:
            amount_num = float("-" + amount_str[:-1] + debit_trans[amount_str[-1]])
        elif amount_str[-1] in credit_trans:
            amount_num = float(amount_str[:-1] + credit_trans[amount_str[-1]])
        return amount_num

    @api.model
    def _check_cfonb(self, data_file):
        return data_file.decode("latin1").strip().startswith("01")

    def _parse_file(self, data_file):
        """ Import a file in French CFONB format"""
        cfonb = self._check_cfonb(data_file)
        if not cfonb:
            return super()._parse_file(data_file)
        result = {}
        # The CFONB spec says you should only have digits, capital letters
        # and * - . /
        # But many banks don't respect that and use regular letters for exemple
        # And I found one (LCL) that even uses caracters with accents
        # So the best method is probably to decode with latin1
        data_file_decoded = data_file.decode("latin1")
        lines = self._cfonb_split_lines(data_file_decoded)
        i = 0
        seq = 1
        account_key = False
        decimals = start_balance = False
        start_balance = end_balance = False
        transactions = []
        for line in lines:
            i += 1
            _logger.debug("Line %d: %s" % (i, line))
            if not line:
                continue
            if len(line) != CFONB_WIDTH:
                raise UserError(
                    _(
                        "Line %d is %d caracters long. All lines of a "
                        "CFONB bank statement file must be 120 caracters long."
                    )
                    % (i, len(line))
                )
            rec_type = line[0:2]
            bank_code = line[2:7]
            guichet_code = line[11:16]
            account_number = line[21:32]
            # Some LCL files are invalid: they leave decimals and
            # currency fields empty on lines that start with '01' and '07',
            # so I give default values in the code for those fields
            currency_code = line[16:19] != "   " and line[16:19] or "EUR"
            account_key = "{}-{}-{}-{}".format(
                bank_code,
                guichet_code,
                account_number,
                currency_code,
            )
            decimals = line[19:20] == " " and 2 or int(line[19:20])
            # decimals=2 for EUR, 0 for XPF
            date_cfonb_str = line[34:40]
            date_dt = False
            if date_cfonb_str != "      ":
                date_dt = datetime.strptime(date_cfonb_str, "%d%m%y")
            if account_number in self._excluded_accounts:
                continue

            if rec_type == "01":
                transactions = []
                start_balance = self._parse_cfonb_amount(line[90:104], decimals)
                if account_key not in result:
                    result[account_key] = {
                        "currency_code": currency_code,
                        "account_number": account_number,
                        "name": account_number,
                        "date": False,
                        "balance_start": start_balance,
                        "balance_end_real": False,
                        "transactions": [],
                    }

            elif rec_type == "07":
                end_balance = self._parse_cfonb_amount(line[90:104], decimals)
                self._cfonb_unique_import_id_postprocess(transactions)
                result[account_key]["balance_end_real"] = end_balance
                result[account_key]["date"] = date_dt
                result[account_key]["transactions"] += transactions

            elif rec_type == "04":
                amount = self._parse_cfonb_amount(line[90:104], decimals)
                ref = line[81:88].strip()  # This is not unique
                name = line[48:79].strip()
                transactions.append(
                    {
                        "sequence": seq,
                        "date": date_dt,
                        "payment_ref": name,
                        "unique_import_id": "{}-{}-{:.2f}-{}".format(
                            fields.Date.to_string(date_dt), ref, amount, name
                        ),
                        "amount": amount,
                    }
                )
                seq += 1

            elif rec_type == "05":
                complementary_info_type = line[45:48]
                complementary_info = line[48:118].strip()
                # Strategy:
                # We use ALL complementary_info_types in unique_import_id
                # because it lowers the risk to get the error
                # caused by 2 different lines with same amount/date/label,
                # but we add the complementary_info in 'payment_ref' only
                # when it's interesting for the user, in order to avoid
                # too long labels with too much "pollution"
                transactions[-1]["unique_import_id"] += complementary_info
                if complementary_info_type in ("   ", "LIB") and complementary_info:
                    transactions[-1]["payment_ref"] += " " + complementary_info

            if rec_type in ("04", "05", "07") and account_key not in result:
                raise UserError(
                    _("The CFONB file is inconsistent. Error on line %d.") % i
                )
        res = []
        for rdict in result.values():
            if rdict["transactions"]:
                res.append(
                    (rdict.pop("currency_code"), rdict.pop("account_number"), [rdict])
                )
        return res

    @api.model
    def _cfonb_unique_import_id_postprocess(self, transactions):
        """In the CFONB spec, there is no requirement for a unique identifier for
        each statement line. The 'ref' (Numéro d'écriture) is often filled with
        zeros. So it's possible to have the same unique_import_id for 2 statement
        lines, for example if you buy a train ticket and then the return train ticket
        on the same day. To avoid an error upon import in this scenario,
        we postprocess the unique_import_id appending '-2', '-3', etc...
        """
        unique_import_ids = {}
        for transaction in transactions:
            unique_import_id = transaction["unique_import_id"]
            if unique_import_id in unique_import_ids:
                unique_import_ids[unique_import_id] += 1
                transaction["unique_import_id"] += (
                    "-%s" % unique_import_ids[unique_import_id]
                )
            else:
                unique_import_ids[unique_import_id] = 1

    def _cfonb_split_lines(self, data_file):
        """Split the data file into lines.

        Returns a list of the lines in the file provided.
        """
        # According to the standard each line has to be 120 chars long, but
        # some banks ship the files without line break.
        # so we want to split the file after 120 chars, no matter if there
        # is a newline there or not.

        # remove linebreaks
        data_file_without_linebreaks = data_file.replace("\n", "").replace("\r", "")

        # check length of file
        max_len = len(data_file_without_linebreaks)
        lines = []

        # make sure the length is a multiple of 120 otherwise it isn't valid
        if max_len % CFONB_WIDTH:
            raise UserError(_("The file is not divisible in 120 char lines"))
        if max_len == 0:
            raise UserError(_("The file is empty."))
        for index in range(0, max_len, CFONB_WIDTH):
            # append a 120 char slice of the file to the list of lines
            lines.append(data_file_without_linebreaks[index : index + CFONB_WIDTH])
        return lines
