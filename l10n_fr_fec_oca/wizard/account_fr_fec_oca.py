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
import csv
import io
import logging

from odoo import api, fields, models
from odoo.exceptions import AccessDenied, UserError
from odoo.tools import SQL, float_is_zero

logger = logging.getLogger(__name__)


class AccountFrFecOca(models.TransientModel):
    _inherit = "l10n_fr.fec.export.wizard"

    company_id = fields.Many2one(
        "res.company",
        ondelete="cascade",
        required=True,
        default=lambda self: self.env.company,
    )
    date_range_id = fields.Many2one(
        "date.range",
        check_company=True,
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
    available_partner_account_ids = fields.Many2many(
        "account.account",
        compute="_compute_available_partner_account_ids",
    )
    partner_account_ids = fields.Many2many(
        "account.account",
        string="Accounts",
        default=lambda self: self._default_partner_account_ids(),
        check_company=True,
        domain="[('id', 'in', available_partner_account_ids)]",
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
    excluded_journal_ids = fields.Many2many(
        "account.journal",
        string="Excluded Journals",
        domain="[('company_id', 'parent_of', company_id)]",
    )
    fec_data = fields.Binary(
        "FEC File",
        readonly=True,
        attachment=True,
    )

    @api.depends("date_range_id")
    def _compute_dates(self):
        for wiz in self:
            if wiz.date_range_id:
                wiz.date_from = wiz.date_range_id.date_start
                wiz.date_to = wiz.date_range_id.date_end

    @api.model
    def _default_partner_account_ids(self):
        IrDefaultSudo = self.env["ir.default"].sudo()
        default_accounts = []
        pay = IrDefaultSudo._get("res.partner", "default_payable_account_id")
        if pay:
            default_accounts.append(pay)
        rec = IrDefaultSudo._get("res.partner", "default_receivable_account_id")
        if rec:
            default_accounts.append(rec)
        return default_accounts or False

    @api.depends("company_id")
    def _compute_available_partner_account_ids(self):
        for wiz in self:
            accounts = self.env["account.account"].search(
                [
                    ("company_ids", "in", [wiz.company_id.id, False]),
                ]
            )
            wiz.available_partner_account_ids = accounts.ids

    def _get_base_domain(self):
        domain = [
            ("company_id", "in", tuple(self.company_id._accessible_branches().ids))
        ]
        # For official report: only use posted entries
        if self.export_type == "official":
            domain.append(("parent_state", "=", "posted"))
        if self.excluded_journal_ids:
            domain.append(("journal_id", "not in", self.excluded_journal_ids.ids))
        # In Odoo 19, the parent wizard removed the 'exclude_zero' field and
        # always excludes zero-balance lines in its base domain. We align on
        # this behavior to stay consistent with l10n_fr_account.
        domain.append(("balance", "!=", 0.0))
        return domain

    def _do_query_unaffected_earnings(self):
        results = super()._do_query_unaffected_earnings()
        # Hack to replace 120 by 129 when it's a loss
        if results[11] != "0,00" and results[12] == "0,00" and results[4] == "120000":
            results[4] = "129000"
            results[5] = "Résultat de l'exercice (perte)"
        return results

    def _get_header_fields(self):
        return [
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

    def _get_aux_fields(self):
        auxlib = SQL(
            """
                COALESCE(replace(account_move_line__partner_id.name, '|', '/'), '')
            """
        )
        auxnum = SQL("account_move_line__partner_id.id::text")
        if self.partner_identifier == "ref":
            auxnum = SQL("""
                COALESCE(
                    NULLIF(replace(
                        account_move_line__partner_id.ref,
                        '|',
                        '/'
                    ), ''),
                    account_move_line__partner_id.id::text
                )
            """)
        if self.partner_option == "receivable_payable":
            aux_sql = SQL(
                """
                    CASE
                        WHEN account_move_line__account_id.account_type IN (
                            'asset_receivable',
                            'liability_payable'
                        )
                        THEN %(auxnum)s
                        ELSE ''
                        END AS CompAuxNum,
                    CASE
                        WHEN account_move_line__account_id.account_type IN (
                            'asset_receivable',
                            'liability_payable'
                        )
                        THEN %(auxlib)s
                        ELSE ''
                        END AS CompAuxLib
                """,
                auxnum=auxnum,
                auxlib=auxlib,
            )
        elif self.partner_option == "accounts":
            partner_account_ids = tuple(self.partner_account_ids.ids)
            aux_sql = SQL(
                """
                    CASE
                        WHEN account_move_line__account_id.id IN %(partner_account_ids)s
                        THEN %(auxnum)s
                        ELSE ''
                        END AS CompAuxNum,
                    CASE
                        WHEN account_move_line__account_id.id IN %(partner_account_ids)s
                        THEN %(auxlib)s
                        ELSE ''
                        END AS CompAuxLib
                """,
                partner_account_ids=partner_account_ids,
                auxnum=auxnum,
                auxlib=auxlib,
            )
        else:
            aux_sql = SQL(
                "%(auxnum)s AS CompAuxNum, %(auxlib)s AS CompAuxLib",
                auxnum=auxnum,
                auxlib=auxlib,
            )
        return aux_sql

    def _get_rows_initial_balance(self, company):
        rows_to_write = []
        currency_digits = 2
        # INITIAL BALANCE
        unaffected_earnings_account = self.env["account.account"].search(
            [
                *self.env["account.account"]._check_company_domain(company),
                ("account_type", "=", "equity_unaffected"),
            ],
            limit=1,
        )
        # used to make sure that we add the unaffected earning initial balance only once
        unaffected_earnings_line = True
        if unaffected_earnings_account:
            # compute the benefit/loss of last year to add
            # in the initial balance of the current year earnings account
            unaffected_earnings_results = self._do_query_unaffected_earnings()
            unaffected_earnings_line = False

        query = self.env["account.move.line"]._search(
            self._get_base_domain()
            + [
                ("date", "<", self.date_from),
                ("account_id.include_initial_balance", "=", True),
                (
                    "account_id.account_type",
                    "not in",
                    ["asset_receivable", "liability_payable"],
                ),
            ]
        )
        aa_name = self.env["account.account"]._field_to_sql(
            "account_move_line__account_id",
            "name",
        )
        aa_code = self.env["account.account"]._field_to_sql(
            "account_move_line__account_id", "code", query
        )
        sql_query = query.select(
            SQL(
                """
                'OUV' AS JournalCode,
                'Balance initiale' AS JournalLib,
                'OUVERTURE/' || %(formatted_date_year)s AS EcritureNum,
                %(formatted_date_from)s AS EcritureDate,
                MIN(%(aa_code)s) AS CompteNum,
                replace(replace(MIN(%(aa_name)s), '|', '/'), '\t', '') AS CompteLib,
                '' AS CompAuxNum,
                '' AS CompAuxLib,
                '-' AS PieceRef,
                %(formatted_date_from)s AS PieceDate,
                '/' AS EcritureLib,
                replace(
                    CASE
                    WHEN sum(account_move_line.balance) <= 0
                    THEN '0,00'
                    ELSE to_char(SUM(account_move_line.balance), '000000000000000D99')
                    END, '.', ',') AS Debit,
                replace(
                    CASE
                    WHEN sum(account_move_line.balance) >= 0
                    THEN '0,00'
                    ELSE to_char(-SUM(account_move_line.balance), '000000000000000D99')
                    END, '.', ',') AS Credit,
                '' AS EcritureLet,
                '' AS DateLet,
                %(formatted_date_from)s AS ValidDate,
                '' AS Montantdevise,
                '' AS Idevise,
                MIN(account_move_line__account_id.id) AS CompteID
            """,
                formatted_date_year=self.date_from.year,
                formatted_date_from=fields.Date.to_string(self.date_from).replace(
                    "-", ""
                ),
                aa_code=aa_code,
                aa_name=aa_name,
            )
        )
        self.env.cr.execute(
            SQL(
                """
                %s
                GROUP BY
                    account_move_line__account_id.id,
                    account_move_line__account_id.account_type
            """,
                sql_query,
            )
        )

        for row in self.env.cr.fetchall():
            listrow = list(row)
            account_id = listrow.pop()
            if not unaffected_earnings_line:
                account = self.env["account.account"].browse(account_id)
                if account.account_type == "equity_unaffected":
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

        if (
            not unaffected_earnings_line
            and unaffected_earnings_results
            and (
                unaffected_earnings_results[11] != "0,00"
                or unaffected_earnings_results[12] != "0,00"
            )
        ):
            unaffected_earnings_account = self.env["account.account"].search(
                [("account_type", "=", "equity_unaffected")], limit=1
            )
            if unaffected_earnings_account:
                unaffected_earnings_results[4] = unaffected_earnings_account.code
                unaffected_earnings_results[5] = unaffected_earnings_account.name
            rows_to_write.append(unaffected_earnings_results)
        return rows_to_write

    def _get_rows_initial_balance_rec_pay(self):
        rows_to_write = []
        query = self.env["account.move.line"]._search(
            self._get_base_domain()
            + [
                ("date", "<", self.date_from),
                ("account_id.include_initial_balance", "=", True),
                (
                    "account_id.account_type",
                    "in",
                    ["asset_receivable", "liability_payable"],
                ),
            ]
        )
        query.left_join(
            "account_move_line", "partner_id", "res_partner", "id", "partner_id"
        )
        aa_name = self.env["account.account"]._field_to_sql(
            "account_move_line__account_id",
            "name",
        )
        aa_code = self.env["account.account"]._field_to_sql(
            "account_move_line__account_id", "code", query
        )
        sql_query = query.select(
            SQL(
                """
                'OUV' AS JournalCode,
                'Balance initiale' AS JournalLib,
                'OUVERTURE/' || %(formatted_date_year)s AS EcritureNum,
                %(formatted_date_from)s AS EcritureDate,
                MIN(%(aa_code)s) AS CompteNum,
                replace(MIN(%(aa_name)s), '|', '/') AS CompteLib,
                %(aux_fields)s,
                '-' AS PieceRef,
                %(formatted_date_from)s AS PieceDate,
                '/' AS EcritureLib,
                replace(
                    CASE
                    WHEN sum(account_move_line.balance) <= 0
                    THEN '0,00'
                    ELSE to_char(SUM(account_move_line.balance), '000000000000000D99')
                    END, '.', ',') AS Debit,
                replace(
                    CASE
                    WHEN sum(account_move_line.balance) >= 0
                    THEN '0,00'
                    ELSE to_char(-SUM(account_move_line.balance), '000000000000000D99')
                    END, '.', ',') AS Credit,
                '' AS EcritureLet,
                '' AS DateLet,
                %(formatted_date_from)s AS ValidDate,
                '' AS Montantdevise,
                '' AS Idevise,
                MIN(account_move_line__account_id.id) AS CompteID
            """,
                formatted_date_year=self.date_from.year,
                formatted_date_from=fields.Date.to_string(self.date_from).replace(
                    "-", ""
                ),
                aa_code=aa_code,
                aa_name=aa_name,
                aux_fields=self._get_aux_fields(),
            )
        )
        self.env.cr.execute(
            SQL(
                """
                %s
                GROUP BY
                    account_move_line__account_id.id,
                    account_move_line__account_id.account_type,
                    account_move_line__partner_id.ref,
                    account_move_line__partner_id.id
            """,
                sql_query,
            )
        )

        for row in self.env.cr.fetchall():
            listrow = list(row)
            listrow.pop()
            rows_to_write.append(listrow)

        return rows_to_write

    def _get_rows_fec_lines(self):
        query_limit = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("l10n_fr_fec.batch_size", 500000)
        )
        query = self.env["account.move.line"]._search(
            domain=self._get_base_domain()
            + [
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
            ],
            limit=query_limit + 1,
            order="date, move_name, id",
        )
        account_alias = query.join(
            "account_move_line", "account_id", "account_account", "id", "account_id"
        )
        aa_name = self.env["account.account"]._field_to_sql(
            account_alias,
            "name",
        )
        aa_code = self.env["account.account"]._field_to_sql(
            account_alias, "code", query
        )
        aj_name = self.env["account.journal"]._field_to_sql(
            "account_move_line__journal_id", "name"
        )
        columns = SQL(
            """
                REGEXP_REPLACE(
                    replace(
                        %(journal_alias)s.code,
                        '|',
                        '/'
                    ), '[\\t\\r\\n]', ' ', 'g'
                ) AS JournalCode,
                REGEXP_REPLACE(
                    replace(
                        %(aj_name)s,
                        '|',
                        '/'
                    ), '[\\t\\r\\n]', ' ', 'g'
                ) AS JournalLib,
                REGEXP_REPLACE(
                    replace(
                        %(move_alias)s.name,
                        '|',
                        '/'
                    ), '[\\t\\r\\n]', ' ', 'g'
                ) AS EcritureNum,
                TO_CHAR(%(move_alias)s.date, 'YYYYMMDD') AS EcritureDate,
                %(aa_code)s AS CompteNum,
                REGEXP_REPLACE(
                    replace(
                        %(aa_name)s,
                        '|',
                        '/'
                    ), '[\\t\\r\\n]', ' ', 'g'
                ) AS CompteLib,
                %(aux_fields)s,
                CASE
                    WHEN %(move_alias)s.ref IS null OR %(move_alias)s.ref = ''
                        THEN '-'
                    ELSE REGEXP_REPLACE(
                        replace(
                            %(move_alias)s.ref,
                            '|',
                            '/'
                        ), '[\\t\\r\\n]', ' ', 'g')
                    END AS PieceRef,
                TO_CHAR(COALESCE(
                    %(move_alias)s.invoice_date,
                    %(move_alias)s.date),
                    'YYYYMMDD'
                ) AS PieceDate,
                CASE
                    WHEN account_move_line.name IS NULL OR account_move_line.name = ''
                        THEN '/'
                    WHEN account_move_line.name SIMILAR TO '[\\t|\\s|\\n]*'
                        THEN '/'
                    ELSE REGEXP_REPLACE(replace(
                        account_move_line.name,
                        '|',
                        '/'), '[\\t\\n\\r]', ' ', 'g')
                    END AS EcritureLib,
                replace(
                    CASE
                        WHEN account_move_line.debit = 0
                        THEN '0,00'
                        ELSE to_char(account_move_line.debit, '000000000000000D99')
                        END, '.', ',') AS Debit,
                replace(
                    CASE
                        WHEN account_move_line.credit = 0
                        THEN '0,00'
                        ELSE to_char(account_move_line.credit, '000000000000000D99')
                        END, '.', ',') AS Credit,
                CASE
                    WHEN %(full_alias)s.id IS NULL
                    THEN ''::text
                    ELSE %(full_alias)s.id::text
                    END AS EcritureLet,
                CASE
                    WHEN account_move_line.full_reconcile_id IS NULL
                    THEN ''
                    ELSE TO_CHAR(%(full_alias)s.create_date, 'YYYYMMDD')
                    END AS DateLet,
                TO_CHAR(%(move_alias)s.date, 'YYYYMMDD') AS ValidDate,
                CASE
                    WHEN
                        account_move_line.amount_currency IS NULL OR
                        account_move_line.amount_currency = 0
                    THEN ''
                    ELSE replace(
                        to_char(
                            account_move_line.amount_currency,
                            '000000000000000D99'
                        ),
                        '.',
                        ','
                    ) END AS Montantdevise,
                CASE
                    WHEN account_move_line.currency_id IS NULL
                    THEN ''
                    ELSE %(currency_alias)s.name
                    END AS Idevise
            """,
            currency_alias=SQL.identifier(
                query.left_join(
                    "account_move_line",
                    "currency_id",
                    "res_currency",
                    "id",
                    "currency_id",
                )
            ),
            full_alias=SQL.identifier(
                query.left_join(
                    "account_move_line",
                    "full_reconcile_id",
                    "account_full_reconcile",
                    "id",
                    "full_reconcile_id",
                )
            ),
            journal_alias=SQL.identifier(
                query.left_join(
                    "account_move_line",
                    "journal_id",
                    "account_journal",
                    "id",
                    "journal_id",
                )
            ),
            move_alias=SQL.identifier(
                query.left_join(
                    "account_move_line", "move_id", "account_move", "id", "move_id"
                )
            ),
            partner_alias=SQL.identifier(
                query.left_join(
                    "account_move_line", "partner_id", "res_partner", "id", "partner_id"
                )
            ),
            account_alias=SQL.identifier(account_alias),
            aj_name=aj_name,
            aa_code=aa_code,
            aa_name=aa_name,
            aux_fields=self._get_aux_fields(),
        )
        rows_to_write = []
        has_more_results = True
        while has_more_results:
            self.env.cr.execute(query.select(columns))
            query.offset += query_limit
            has_more_results = (
                self.env.cr.rowcount > query_limit
            )  # we load one more result than the limit to check if there is more
            query_results = self.env.cr.fetchall()
            rows_to_write.append(query_results[:query_limit])
        return rows_to_write

    def _convert_delimiter(self, delimiter):
        if delimiter == "tab":
            return "\t"
        return delimiter

    # flake8: noqa: C901
    def generate_fec_content(self):
        # We choose to implement the flat file instead of the XML file for 2 reasons :
        # 1) the XSD file impose to have the label on the account.move,
        # but Odoo has the label on the account.move.line,
        # so that's a  problem !
        # 2) CSV files are easier to read/use for a regular accountant.
        # So it will be easier for the accountant to check
        # the file before sending it to the fiscal administration
        company = self.company_id
        delimiter = self._convert_delimiter(self.delimiter)
        # HEADER
        rows_to_write = [self._get_header_fields()]
        # INITIAL BALANCE
        rows_to_write.extend(self._get_rows_initial_balance(company))
        # INITIAL BALANCE - receivable/payable
        rows_to_write.extend(self._get_rows_initial_balance_rec_pay())
        # LINES
        fec_lines = self._get_rows_fec_lines()
        with io.StringIO() as fecfile:
            csv_writer = csv.writer(fecfile, delimiter=delimiter, lineterminator="\r\n")

            # Write header and initial balances
            csv_writer.writerows(rows_to_write)

            # Write current period's data
            for query_result in fec_lines:
                csv_writer.writerows(query_result)
            try:
                content = fecfile.getvalue()[:-2].encode(self.encoding)
            except UnicodeEncodeError:
                raise UserError(
                    self.env._(
                        "Your file cannot be encoded in %s. "
                        "Please choose another encoding."
                    )
                    % self.encoding
                ) from None
        return content

    def generate_fec(self):
        company = self.company_id
        company_legal_data = self._get_company_legal_data(company)
        end_date = fields.Date.to_string(self.date_to).replace("-", "")
        suffix = ""
        if self.export_type == "nonofficial":
            suffix = "-NONOFFICIAL"
        extension = self.env.context.get("extension", "csv")

        # Generate content
        content = self.generate_fec_content()

        # Set fiscal year lock date to the end date (not in test)
        fiscalyear_lock_date = company.fiscalyear_lock_date
        if not self.test_file and (
            not fiscalyear_lock_date or fiscalyear_lock_date < self.date_to
        ):
            company.write({"fiscalyear_lock_date": self.date_to})

        return {
            "file_name": f"{company_legal_data}FEC{end_date}{suffix}.{extension}",
            "file_content": content,
            "file_type": f"{extension}",
        }

    def create_fec_report_action(self):
        if not (
            self.env.is_admin() or self.env.user.has_group("account.group_account_user")
        ):
            raise AccessDenied()
        if self.date_from >= self.date_to:
            raise UserError(self.env._("The start date must be before the end date."))
        file_data = self.generate_fec()
        self.write(
            {
                "fec_data": base64.encodebytes(file_data["file_content"]),
                # Filename = <siren>FECYYYYMMDD where YYYMMDD is the closing date
                "filename": file_data["file_name"],
            }
        )

        return {
            "name": "FEC",
            "type": "ir.actions.act_url",
            "url": (
                f"web/content/?model={self._name}&id={self.id}"
                f"&filename_field=filename&field=fec_data&download=true"
                f"&filename={self.filename}"
            ),
            "target": "self",
        }
