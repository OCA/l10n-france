# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import datetime
from csv import QUOTE_MINIMAL, Dialect, register_dialect

from odoo.addons.account_move_base_import.parser.file_parser import (
    FileParser,
    float_or_zero,
)

# file has no header... Define one
monetico_header = [
    "date_recouvrement_paiement",
    "num_tpe",
    "ref_paiement",
    "etat_paiement",
    "date_demande_paiement",
    "heure_demande_paiement",
    "montant",
    "devise",
    "numero_authorisation",
    "code_retour",
    "reference_archivage",
    "type_carte",
    "date_validite",
    "cryptogramme_visuel",
    "ref_libre_paiement",
    "niveau_3dsecure",
    "numero_cb",
    "pays_origine_cb",
    "aliad_cb",
    "ip_client",
    "pays_origine_transaction",
]


class MoneticoDialect(Dialect):
    delimiter = ";"
    quotechar = '"'
    doublequote = False
    skipinitialspace = False
    lineterminator = "\n"
    quoting = QUOTE_MINIMAL


register_dialect("monetico_dialect", MoneticoDialect)


class MoneticoFileParser(FileParser):
    def __init__(self, journal, ftype="csv", **kwargs):
        conversion_dict = {
            "date_recouvrement_paiement": datetime.datetime,
            "montant": float_or_zero,
            "ref_paiement": str,
            "etat_paiement": str,
        }
        super().__init__(
            journal,
            ftype=ftype,
            extra_fields=conversion_dict,
            dialect=MoneticoDialect,
            header=monetico_header,
            **kwargs,
        )

    @classmethod
    def parser_for(cls, parser_name):
        """
        Used by the new_bank_statement_parser class factory. Return true if
        the providen name is generic_csvxls_so
        """
        return parser_name == "monetico_cb_csvparser"

    def get_move_line_vals(self, line, *args, **kwargs):
        res = {
            "name": line.get("ref_paiement", ""),
            "credit": line["montant"] > 0.0 and line["montant"] or 0.0,
            "debit": line["montant"] < 0.0 and -line["montant"] or 0.0,
        }
        return res

    def _post(self, *args, **kwargs):
        res = super()._post(*args, **kwargs)
        final_rows = []
        for row in self.result_row_list:
            if row.get("etat_paiement") in ("PA",):  # Payé
                final_rows.append(row)
            payment_date = row.get("date_recouvrement_paiement")
            if not self.move_date or payment_date > self.move_date:
                self.move_date = payment_date
        self.result_row_list = final_rows
        return res
