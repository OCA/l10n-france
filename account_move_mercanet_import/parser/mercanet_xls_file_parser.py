# Copyright 2025  Akretion (https://www.akretion.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import datetime
from csv import QUOTE_MINIMAL, Dialect, register_dialect

from odoo.addons.account_move_base_import.parser.file_parser import FileParser


def float_or_zero(val):
    """Conversion function used to manage
    empty string into float usecase"""
    val = val.strip()
    return (float(val.replace(",", ".")) if val else 0.0) / 100.0


class MercanetDialect(Dialect):
    delimiter = "\t"
    quotechar = '"'
    doublequote = False
    skipinitialspace = False
    lineterminator = "\n"
    quoting = QUOTE_MINIMAL


register_dialect("mercanet_dialect", MercanetDialect)


class MercanetFileParser(FileParser):
    def __init__(self, journal, ftype="csv", **kwargs):
        conversion_dict = {
            "operationDateTime": datetime.datetime,
            "operationAmount": float_or_zero,
            "transactionReference": str,
            "newStatus": str,
        }
        super().__init__(
            journal,
            ftype="csv",  # force format because extension is xls
            extra_fields=conversion_dict,
            dialect=MercanetDialect,
            **kwargs,
        )

    @classmethod
    def parser_for(cls, parser_name):
        """
        Used by the new_bank_statement_parser class factory. Return true if
        the providen name is generic_csvxls_so
        """
        return parser_name == "mercanet_cb_csvparser"

    def _pre(self, *args, **kwargs):
        split_file = self.filebuffer.decode("utf-8").split("\n")
        selected_lines = []
        # delete first ligne TITLE
        for line in split_file[1:]:
            # delete prefix tab20 format
            if line.startswith("HEADER"):
                line = line[7:]
            elif line.startswith("OPERATION"):
                line = line[10:]
            elif line.startswith("END"):
                break
            selected_lines.append(line.strip())
        self.filebuffer = "\n".join(selected_lines)
        self.filebuffer = self.filebuffer.encode("utf-8")

    def get_move_line_vals(self, line, *args, **kwargs):
        res = {
            "name": line.get("transactionReference", ""),
            "credit": line["operationAmount"] > 0.0 and line["operationAmount"] or 0.0,
            "debit": line["operationAmount"] < 0.0 and -line["operationAmount"] or 0.0,
            "date": line["operationDateTime"],
        }
        return res
