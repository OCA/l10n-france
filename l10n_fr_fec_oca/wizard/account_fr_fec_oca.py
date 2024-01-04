# Copyright 2013-2020 Akretion France (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2016-2020 Odoo SA (https://www.odoo.com/fr_FR/)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

# This module is a fork of l10n_fr_fec from official addons
# (which itself was copied from OCA with my authorisation)
# The construction of SQL requests don't respect pylint E8103
# The problem is that fixing this would require large changes in the code
# which would make this module a deeper fork of l10n_fr_fec
# and would make it more difficult to compare the 2 modules and port
# changes/improvements between each other
# pylint: skip-file

import base64
import io
import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied, UserError
from odoo.tools import float_is_zero

logger = logging.getLogger(__name__)

try:
    from unidecode import unidecode
except ImportError:
    logger.debug("Cannot import unidecode")
try:
    import unicodecsv
except ImportError:
    logger.debug("Cannot import unicodecsv")


class AccountFrFecOca(models.TransientModel):
    _name = "account.fr.fec.oca"
    _description = "Ficher Echange Informatise"
    _check_company_auto = True

    company_id = fields.Many2one(
        "res.company",
        ondelete="cascade",
        required=True,
        default=lambda self: self.env.company,
    )
    date_range_id = fields.Many2one(
        "date.range",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    date_from = fields.Date(
        compute="_compute_dates",
        string="Start Date",
        required=True,
        readonly=False,
        store=True,
    )
    date_to = fields.Date(
        compute="_compute_dates",
        string="End Date",
        required=True,
        readonly=False,
        store=True,
    )
    encoding = fields.Selection(
        [
            ("iso8859_15", "ISO-8859-15"),
            ("utf-8", "UTF-8"),
            ("ascii", "ASCII"),
        ],
        default="iso8859_15",
        required=True,
    )
    delimiter = fields.Selection(
        [
            ("|", "|"),
            ("tab", "Tab"),
        ],
        default="|",
        string="Field Delimiter",
        required=True,
    )
    partner_option = fields.Selection(
        [
            ("receivable_payable", "Receivable and Payable Accounts"),
            ("accounts", "Selected Accounts"),
            ("all", "All"),
        ],
        default="receivable_payable",
        required=True,
        string="Partner Export Option",
    )
    partner_account_ids = fields.Many2many(
        "account.account",
        string="Accounts",
        default=lambda self: self._default_partner_account_ids(),
        check_company=True,
        domain="[('company_id', '=', company_id)]",
    )
    partner_identifier = fields.Selection(
        [
            ("id", "ID"),
            ("ref", "Reference"),
        ],
        required=True,
        default="id",
        help="Field on partner used for the column CompAuxNum. If you select "
        "'Reference', make sure all partners used in journal items have a Reference "
        "and that this reference is unique.",
    )
    fec_data = fields.Binary("FEC File", readonly=True, attachment=True)
    filename = fields.Char(size=256, readonly=True)
    export_type = fields.Selection(
        [
            ("official", "Official FEC report (posted entries only)"),
            ("nonofficial", "Non-official FEC report (posted and draft entries)"),
        ],
        required=True,
        default="official",
    )

    @api.depends("date_range_id")
    def _compute_dates(self):
        for wiz in self:
            if wiz.date_range_id:
                wiz.date_from = wiz.date_range_id.date_start
                wiz.date_to = wiz.date_range_id.date_end

    @api.model
    def _default_partner_account_ids(self):
        pay = self.env["ir.property"]._get("property_account_payable_id", "res.partner")
        rec = self.env["ir.property"]._get(
            "property_account_receivable_id", "res.partner"
        )
        return pay + rec

    def _do_query_unaffected_earnings(self):
        """Compute the sum of ending balances for all accounts that are
        of a type that does not bring forward the balance in new fiscal years.
        This is needed because we have to display only one line for the initial
        balance of all expense/revenue accounts in the FEC.
        """
        # BENEFIT and LOSS
        sql_query = """
        SELECT
            'OUV' AS JournalCode,
            'Balance initiale' AS JournalLib,
            'OUVERTURE/' || %(formatted_date_year)s AS EcritureNum,
            %(formatted_date_from)s AS EcritureDate,
            '120000' AS CompteNum,
            E'Résultat de l\\'exercice (Bénéfice)' AS CompteLib,
            '' AS CompAuxNum,
            '' AS CompAuxLib,
            '-' AS PieceRef,
            %(formatted_date_from)s AS PieceDate,
            'Report à nouveau' AS EcritureLib,
            replace(
                CASE WHEN COALESCE(sum(aml.balance), 0) <= 0
                THEN '0,00'
                ELSE to_char(SUM(aml.balance), '000000000000000D99')
                END, '.', ',') AS Debit,
            replace(
                CASE WHEN COALESCE(sum(aml.balance), 0) >= 0
                THEN '0,00'
                ELSE to_char(-SUM(aml.balance), '000000000000000D99')
                END, '.', ',') AS Credit,
            '' AS EcritureLet,
            '' AS DateLet,
            %(formatted_date_from)s AS ValidDate,
            '' AS Montantdevise,
            '' AS Idevise
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id = aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
        WHERE
            am.date < %(date_from)s
            AND am.company_id = %(company_id)s
            AND aa.include_initial_balance IS NOT true
            AND (aml.debit != 0 OR aml.credit != 0)
        """
        # For official report: only use posted entries
        if self.export_type == "official":
            sql_query += " AND am.state = 'posted' "
        else:
            sql_query += " AND am.state IN ('draft', 'posted') "
        company = self.company_id
        formatted_date_from = fields.Date.to_string(self.date_from).replace("-", "")
        date_from = self.date_from
        formatted_date_year = date_from.year
        self._cr.execute(
            sql_query,
            {
                "formatted_date_year": formatted_date_year,
                "formatted_date_from": formatted_date_from,
                "date_from": self.date_from,
                "company_id": company.id,
            },
        )
        listrow = []
        row = self._cr.fetchone()
        listrow = list(row)
        # Hack to replace 120 by 129 when it's a loss
        if listrow[11] != "0,00" and listrow[12] == "0,00" and listrow[4] == "120000":
            listrow[4] = "129000"
            listrow[5] = "Résultat de l'exercice (perte)"
        return listrow

    def _get_siren(self, company):
        # Get SIREN from SIRET and not from VAT
        # so that it also work on companies that are not subject to VAT
        if not company.siret:
            raise UserError(_("Missing SIRET on company %s.") % company.display_name)
        siren = company.siret[:9]
        return siren

    def _get_aux_fields(self, sql_args):
        aux_dict = {
            "auxlib": """
        COALESCE(REGEXP_REPLACE(replace(rp.name, '|', '/'), '[\\t\\r\\n]', ' ', 'g'), '')
        """
        }
        if self.partner_identifier == "ref":
            aux_dict[
                "auxnum"
            ] = """
            CASE WHEN rp.ref IS null OR rp.ref = ''
            THEN COALESCE('ID' || rp.id, '')
            ELSE REGEXP_REPLACE(replace(rp.ref, '|', '/'), '[\\t\\r\\n]', ' ', 'g')
            END
            """
        else:
            aux_dict["auxnum"] = """rp.id::text"""

        if self.partner_option == "receivable_payable":
            aux_sql = (
                """
            CASE WHEN aa.account_type IN ('asset_receivable', 'liability_payable')
            THEN %(auxnum)s
            ELSE ''
            END
            AS CompAuxNum,
            CASE WHEN aa.account_type IN ('asset_receivable', 'liability_payable')
            THEN %(auxlib)s
            ELSE ''
            END
            AS CompAuxLib,
            """
                % aux_dict
            )
        elif self.partner_option == "accounts":
            sql_args["partner_account_ids"] = tuple(self.partner_account_ids.ids)
            aux_sql = (
                """
            CASE WHEN aa.id IN %%(partner_account_ids)s
            THEN %(auxnum)s
            ELSE ''
            END
            AS CompAuxNum,
            CASE WHEN aa.id IN %%(partner_account_ids)s
            THEN %(auxlib)s
            ELSE ''
            END
            AS CompAuxLib,
            """
                % aux_dict
            )
        else:
            aux_sql = (
                """
            %(auxnum)s AS CompAuxNum, %(auxlib)s AS CompAuxLib,
            """
                % aux_dict
            )
        return aux_sql

    # flake8: noqa: C901
    def generate_fec(self):
        self.ensure_one()
        if not (
            self.env.is_admin() or self.env.user.has_group("account.group_account_user")
        ):
            raise AccessDenied()
        # We choose to implement the flat file instead of the XML
        # file for 2 reasons :
        # 1) the XSD file impose to have the label on the account.move
        # but Odoo has the label on the account.move.line, so that's a
        # problem !
        # 2) CSV files are easier to read/use for a regular accountant.
        # So it will be easier for the accountant to check the file before
        # sending it to the fiscal administration
        if self.date_from >= self.date_to:
            raise UserError(_("The start date must be before the end date."))

        company = self.company_id

        header = [
            "JournalCode",  # 0
            "JournalLib",  # 1
            "EcritureNum",  # 2
            "EcritureDate",  # 3
            "CompteNum",  # 4
            "CompteLib",  # 5
            "CompAuxNum",  # 6
            "CompAuxLib",  # 7
            "PieceRef",  # 8
            "PieceDate",  # 9
            "EcritureLib",  # 10
            "Debit",  # 11
            "Credit",  # 12
            "EcritureLet",  # 13
            "DateLet",  # 14
            "ValidDate",  # 15
            "Montantdevise",  # 16
            "Idevise",  # 17
        ]

        rows_to_write = [header]
        unaffected_earnings_account = self.env["account.account"].search(
            [
                ("account_type", "=", "equity_unaffected"),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        # used to make sure that we add the unaffected earning initial balance
        # only once
        unaffected_earnings_line = True
        if unaffected_earnings_account:
            # compute the benefit/loss of last year to add in the
            # initial balance of the current year earnings account
            unaffected_earnings_results = self._do_query_unaffected_earnings()
            unaffected_earnings_line = False

        # INITIAL BALANCE other than payable/receivable
        sql_query = """
        SELECT
            'OUV' AS JournalCode,
            'Balance initiale' AS JournalLib,
            'OUVERTURE/' || %(formatted_date_year)s AS EcritureNum,
            %(formatted_date_from)s AS EcritureDate,
            MIN(aa.code) AS CompteNum,
            replace(replace(MIN(aa.name), '|', '/'), '\t', '') AS CompteLib,
            '' AS CompAuxNum,
            '' AS CompAuxLib,
            '-' AS PieceRef,
            %(formatted_date_from)s AS PieceDate,
            'Report à nouveau' AS EcritureLib,
            replace(
                CASE WHEN sum(aml.balance) <= 0
                THEN '0,00'
                ELSE to_char(SUM(aml.balance), '000000000000000D99')
                END, '.', ',') AS Debit,
            replace(
                CASE WHEN sum(aml.balance) >= 0
                THEN '0,00'
                ELSE to_char(-SUM(aml.balance), '000000000000000D99')
                END, '.', ',') AS Credit,
            '' AS EcritureLet,
            '' AS DateLet,
            %(formatted_date_from)s AS ValidDate,
            '' AS Montantdevise,
            '' AS Idevise,
            MIN(aa.id) AS CompteID
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id = aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
        WHERE
            am.date < %(date_from)s
            AND am.company_id = %(company_id)s
            AND aa.include_initial_balance IS true
            AND (aml.debit != 0 OR aml.credit != 0)
        """

        # For official report: only use posted entries
        if self.export_type == "official":
            sql_query += " AND am.state = 'posted' "
        else:
            sql_query += " AND am.state IN ('draft', 'posted') "

        sql_query += """
        GROUP BY aml.account_id, aa.account_type
        HAVING round(sum(aml.balance), %(currency_digits)s) != 0
        AND aa.account_type not in ('asset_receivable', 'liability_payable')
        """
        formatted_date_from = fields.Date.to_string(self.date_from).replace("-", "")
        currency_digits = 2

        sql_args = {  # Use for the 2 INITIAL BALANCEs and for LINES
            "formatted_date_year": self.date_from.year,
            "formatted_date_from": formatted_date_from,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "company_id": company.id,
            "currency_digits": currency_digits,
        }

        self._cr.execute(sql_query, sql_args)
        for row in self._cr.fetchall():
            listrow = list(row)
            account_id = listrow.pop()
            if not unaffected_earnings_line:
                account = self.env["account.account"].browse(account_id)
                if account.account_type == "equity_unaffected":
                    # add the benefit/loss of previous fiscal year to
                    # the first unaffected earnings account found.
                    # Alexis note: on a normal accounting DB, we should
                    # never enter in the IF above because the account
                    # 120000 is supposed to have a balance at 0 at the end
                    # of each fiscal year, because benefit or loss
                    # is supposed to be re-affected by the general assembly
                    # during the year
                    unaffected_earnings_line = True
                    current_amount = float(listrow[11].replace(",", ".")) - float(
                        listrow[12].replace(",", ".")
                    )
                    unaffected_earnings_amount = float(
                        unaffected_earnings_results[11].replace(",", ".")
                    ) - float(unaffected_earnings_results[12].replace(",", "."))
                    listrow_amount = current_amount + unaffected_earnings_amount
                    if float_is_zero(listrow_amount, precision_digits=currency_digits):
                        continue
                    if listrow_amount > 0:
                        listrow[11] = str(listrow_amount).replace(".", ",")
                        listrow[12] = "0,00"
                    else:
                        listrow[11] = "0,00"
                        listrow[12] = str(-listrow_amount).replace(".", ",")
            rows_to_write.append(listrow)

        # if the unaffected earnings account wasn't in the selection yet:
        # add it manually
        if (
            not unaffected_earnings_line
            and unaffected_earnings_results
            and (
                unaffected_earnings_results[11] != "0,00"
                or unaffected_earnings_results[12] != "0,00"
            )
        ):
            # search an unaffected earnings account
            unaffected_earnings_account = self.env["account.account"].search(
                [
                    ("account_type", "=", "equity_unaffected"),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )

            if unaffected_earnings_account:
                unaffected_earnings_results[4] = unaffected_earnings_account.code
                unaffected_earnings_results[5] = unaffected_earnings_account.name
            rows_to_write.append(unaffected_earnings_results)

        aux_fields = self._get_aux_fields(sql_args)

        aux_fields_ini_bal = aux_fields.replace("aa.id IN", "MIN(aa.id) IN").replace(
            "aat.id IN", "MIN(aat.id) IN"
        )
        # INITIAL BALANCE - receivable/payable
        sql_query = (
            """
        SELECT
            'OUV' AS JournalCode,
            'Balance initiale' AS JournalLib,
            'OUVERTURE/' || %(formatted_date_year)s AS EcritureNum,
            %(formatted_date_from)s AS EcritureDate,
            MIN(aa.code) AS CompteNum,
            replace(MIN(aa.name), '|', '/') AS CompteLib,
        """
            + aux_fields_ini_bal
            + """
            '-' AS PieceRef,
            %(formatted_date_from)s AS PieceDate,
            'Report à nouveau' AS EcritureLib,
            replace(
                CASE WHEN sum(aml.balance) <= 0
                THEN '0,00'
                ELSE to_char(SUM(aml.balance), '000000000000000D99')
                END, '.', ',') AS Debit,
            replace(
                CASE WHEN sum(aml.balance) >= 0
                THEN '0,00'
                ELSE to_char(-SUM(aml.balance), '000000000000000D99')
                END, '.', ',') AS Credit,
            '' AS EcritureLet,
            '' AS DateLet,
            %(formatted_date_from)s AS ValidDate,
            '' AS Montantdevise,
            '' AS Idevise,
            MIN(aa.id) AS CompteID
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id=aml.move_id
            LEFT JOIN res_partner rp ON rp.id=aml.partner_id
            JOIN account_account aa ON aa.id = aml.account_id
        WHERE
            am.date < %(date_from)s
            AND am.company_id = %(company_id)s
            AND aa.include_initial_balance IS true
            AND (aml.debit != 0 OR aml.credit != 0)
        """
        )

        # For official report: only use posted entries
        if self.export_type == "official":
            sql_query += " AND am.state = 'posted' "
        else:
            sql_query += " AND am.state IN ('draft', 'posted') "

        sql_query += """
        GROUP BY aml.account_id, aa.account_type, rp.ref, rp.id
        HAVING round(sum(aml.balance), %(currency_digits)s) != 0
        AND aa.account_type in ('asset_receivable', 'liability_payable')
        """
        self._cr.execute(sql_query, sql_args)

        for row in self._cr.fetchall():
            listrow = list(row)
            account_id = listrow.pop()
            rows_to_write.append(listrow)

        # LINES
        sql_query = (
            """
        SELECT
            REGEXP_REPLACE(replace(aj.code, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS JournalCode,
            REGEXP_REPLACE(replace(aj.name, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS JournalLib,
            REGEXP_REPLACE(replace(am.name, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS EcritureNum,
            TO_CHAR(am.date, 'YYYYMMDD') AS EcritureDate,
            aa.code AS CompteNum,
            REGEXP_REPLACE(replace(aa.name, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS CompteLib,
        """
            + aux_fields
            + """
            CASE
                WHEN am.ref IS null OR am.ref = ''
                THEN '-'
                ELSE REGEXP_REPLACE(replace(am.ref, '|', '/'), '[\\t\\r\\n]', ' ', 'g')
            END AS PieceRef,
            TO_CHAR(am.date, 'YYYYMMDD') AS PieceDate,
            CASE WHEN aml.name IS NULL OR aml.name = '' THEN '/'
                WHEN aml.name SIMILAR TO '[\\t|\\s|\\n]*' THEN '/'
                ELSE REGEXP_REPLACE(replace(aml.name, '|', '/'), '[\\t\\n\\r]', ' ', 'g')
            END AS EcritureLib,
            replace(
                CASE WHEN aml.debit = 0
                THEN '0,00'
                ELSE to_char(aml.debit, '000000000000000D99')
                END, '.', ',') AS Debit,
            replace(
                CASE WHEN aml.credit = 0
                THEN '0,00'
                ELSE to_char(aml.credit, '000000000000000D99')
                END, '.', ',') AS Credit,
            CASE WHEN rec.name IS NULL
            THEN ''
            ELSE rec.name
            END AS EcritureLet,
            CASE
                WHEN aml.full_reconcile_id IS NULL
                THEN ''
                ELSE TO_CHAR(rec.create_date, 'YYYYMMDD')
            END AS DateLet,
            TO_CHAR(am.date, 'YYYYMMDD') AS ValidDate,
            CASE
                WHEN aml.currency_id IS NULL OR aml.currency_id = aml.company_currency_id OR aml.amount_currency IS NULL OR aml.amount_currency = 0
                THEN ''
                ELSE replace(to_char(
                    aml.amount_currency, '000000000000000D99'), '.', ',')
            END AS Montantdevise,
            CASE
                WHEN aml.currency_id IS NULL OR aml.currency_id = aml.company_currency_id OR aml.amount_currency IS NULL OR aml.amount_currency = 0
                THEN ''
                ELSE rc.name
            END AS Idevise
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id=aml.move_id
            LEFT JOIN res_partner rp ON rp.id=aml.partner_id
            JOIN account_journal aj ON aj.id = am.journal_id
            JOIN account_account aa ON aa.id = aml.account_id
            LEFT JOIN res_currency rc ON rc.id = aml.currency_id
            LEFT JOIN account_full_reconcile rec
                ON rec.id = aml.full_reconcile_id
        WHERE
            am.date >= %(date_from)s
            AND am.date <= %(date_to)s
            AND am.company_id = %(company_id)s
            AND (aml.debit != 0 OR aml.credit != 0)
        """
        )

        # For official report: only use posted entries
        if self.export_type == "official":
            sql_query += " AND am.state = 'posted' "
        else:
            sql_query += " AND am.state IN ('draft', 'posted') "

        sql_query += """
        ORDER BY
            am.date,
            am.name,
            aml.id
        """
        self._cr.execute(sql_query, sql_args)

        for row in self._cr.fetchall():
            rows_to_write.append(list(row))

        fecvalue = self._csv_write_rows(rows_to_write)
        end_date = fields.Date.to_string(self.date_to).replace("-", "")
        suffix = ""
        if self.export_type == "nonofficial":
            suffix = "-NONOFFICIAL"

        siren = self._get_siren(company)
        self.write(
            {
                "fec_data": base64.encodebytes(fecvalue),
                # Filename = <siren>FECYYYYMMDD where YYYMMDD is the closing date
                "filename": "%sFEC%s%s.txt" % (siren, end_date, suffix),
            }
        )

        action = {
            "name": "FEC",
            "type": "ir.actions.act_url",
            "url": "web/content/?model=%s&id=%d&filename_field=filename&"
            "field=fec_data&download=true&filename=%s"
            % (self._name, self.id, self.filename),
            "target": "self",
        }
        return action

    def _csv_write_rows(self, rows):
        """
        Write FEC rows into a file
        It seems that Bercy's bureaucracy is not too happy about the
        empty new line at the End Of File.

        @param {list(list)} rows: the list of rows. Each row is a list of
        strings

        @return the value of the file
        """
        fecfile = io.BytesIO()
        encoding = self.encoding
        delimiter = self.delimiter
        if delimiter == "tab":
            delimiter = "\t"
        writer = unicodecsv.writer(
            fecfile,
            delimiter=delimiter,
            lineterminator="\r\n",
            encoding=encoding,
            errors="replace",
        )
        for row in rows:
            if encoding == "ascii":
                for j, _cell_content in enumerate(row):
                    row[j] = unidecode(row[j])
            writer.writerow(row)

        fecvalue = fecfile.getvalue()
        fecfile.close()
        return fecvalue
