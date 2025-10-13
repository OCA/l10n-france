# Copyright 2025 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class TrialBalanceEBP(models.AbstractModel):
    _name = "report.account_balance_ebp_csv_export.trial_balance_ebp_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "EBP XLSX Trial Balance"

    def generate_xlsx_report(self, workbook, data, objects):
        sheet = workbook.add_worksheet("EBPbalance")
        i = 0
        company = objects.company_id
        ccur = company.currency_id
        styles = self._prepare_styles(workbook, ccur)
        # Header line
        sheet.write(i, 0, "Compte.Numero", styles["col_title"])
        sheet.set_column(0, 0, 15)
        sheet.write(i, 1, "Compte.Intitule", styles["col_title"])
        sheet.set_column(1, 1, 50)
        sheet.write(i, 2, "Balance.SldCptNDebit", styles["col_title"])
        sheet.set_column(2, 5, 20)
        sheet.write(i, 3, "Balance.SldCptNCredit", styles["col_title"])
        sheet.write(i, 4, "Balance.SldCptNSoldeD", styles["col_title"])
        sheet.write(i, 5, "Balance.SldCptNSolde", styles["col_title"])
        model = self.env["report.account_financial_report.trial_balance"]
        res = model._get_report_values(objects.ids, data)
        # Content lines
        for bal in res["trial_balance"]:
            i += 1
            sheet.write(i, 0, bal["code"], styles["string"])
            sheet.write(i, 1, bal["name"], styles["string_small"])
            sheet.write(i, 2, ccur.round(bal["debit"]), styles["currency"])
            sheet.write(i, 3, ccur.round(bal["credit"]), styles["currency"])
            if ccur.compare_amounts(bal["ending_balance"], 0) > 0:
                end_bal_positive = ccur.round(bal["ending_balance"])
                end_bal_negative = 0.0
            else:
                end_bal_positive = 0.0
                end_bal_negative = ccur.round(bal["ending_balance"]) * -1
            sheet.write(i, 4, end_bal_positive, styles["currency"])
            sheet.write(i, 5, end_bal_negative, styles["currency"])

    def _prepare_styles(self, workbook, company_currency):
        col_title_bg_color = "#eeeeee"  # light grey
        font_size = 11
        small_font_size = 10
        decimals = "0" * company_currency.decimal_places
        currency_num_format = f"# ##0.{decimals}"
        styles = {
            "col_title": workbook.add_format(
                {
                    "bg_color": col_title_bg_color,
                    "bold": True,
                    "text_wrap": True,
                    "font_size": small_font_size,
                    "align": "center",
                }
            ),
            "currency": workbook.add_format(
                {"num_format": currency_num_format, "font_size": font_size}
            ),
            "string": workbook.add_format({"font_size": font_size}),
            "string_small": workbook.add_format({"font_size": small_font_size}),
        }
        return styles
