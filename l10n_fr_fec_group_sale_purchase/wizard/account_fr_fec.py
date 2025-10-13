import base64
import csv
import io

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL
from odoo.tools.float_utils import float_is_zero


class AccountFrFecOca(models.TransientModel):
    _inherit = "account.fr.fec.oca"

    group_sale_purchase = fields.Boolean(
        "Group Sale and Purchase Journals",
        default=True,
    )

    def _get_siren(self, company):
        # If the company does not have a SIRET,
        # fallback to using VAT instead.
        if company.siret:
            return super()._get_siren(company)

        dom_tom_group = self.env.ref("l10n_fr.dom-tom")
        is_dom_tom = company.country_id.code in dom_tom_group.country_ids.mapped("code")
        if not is_dom_tom and not company.vat:
            raise UserError(
                self.env._("Missing VAT number for company %s", company.display_name)
            )
        vat = company.vat.upper().replace(" ", "")
        if not is_dom_tom and vat[0:2] != "FR":
            raise UserError(self.env._("FEC is for French companies only!"))

        siren = vat[4:13] if not is_dom_tom else ""
        return siren

    def _sql_query_fec_lines(self, query, **kwargs):
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
                CASE WHEN %(account_alias)s.account_type IN
                    ('asset_receivable', 'liability_payable')
                THEN
                    CASE WHEN %(partner_alias)s.ref IS null OR
                        %(partner_alias)s.ref = ''
                    THEN %(partner_alias)s.id::text
                    ELSE replace(%(partner_alias)s.ref, '|', '/')
                    END
                ELSE ''
                END
                AS CompAuxNum,
                CASE WHEN %(account_alias)s.account_type IN
                    ('asset_receivable', 'liability_payable')
                    THEN COALESCE(REGEXP_REPLACE(replace(
                        %(partner_alias)s.name, '|', '/'),
                        '[\\t\\r\\n]', ' ', 'g'), '')
                    ELSE ''
                END AS CompAuxLib,
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
                        ELSE TO_CHAR(account_move_line.debit, '000000000000000D99')
                        END, '.', ',') AS Debit,
                replace(
                    CASE
                        WHEN account_move_line.credit = 0
                        THEN '0,00'
                        ELSE TO_CHAR(account_move_line.credit, '000000000000000D99')
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
                        TO_CHAR(
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
            account_alias=SQL.identifier(kwargs.get("account_alias")),
            aj_name=kwargs.get("aj_name"),
            aa_code=kwargs.get("aa_code"),
            aa_name=kwargs.get("aa_name"),
        )
        return columns

    def _sql_query_fec_lines2(self, query, **kwargs):
        columns = SQL(
            """
                REGEXP_REPLACE(
                    replace(
                        STRING_AGG(DISTINCT %(journal_alias)s.code, ';'),
                        '|',
                        '/'
                    ), '[\\t\\r\\n]', ' ', 'g'
                ) AS JournalCode,
                REGEXP_REPLACE(
                    replace(
                        STRING_AGG(DISTINCT %(aj_name)s, ';'),
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
                TO_CHAR(MAX(%(move_alias)s.date), 'YYYYMMDD') AS EcritureDate,
                STRING_AGG(DISTINCT %(aa_code)s, ';') AS CompteNum,
                REGEXP_REPLACE(
                    replace(
                        STRING_AGG(DISTINCT %(aa_name)s, ';'),
                        '|',
                        '/'
                    ), '[\\t\\r\\n]', ' ', 'g'
                ) AS CompteLib,
                CASE WHEN %(account_alias)s.account_type IN
                    ('asset_receivable', 'liability_payable')
                THEN
                    CASE WHEN %(partner_alias)s.ref IS null OR
                        %(partner_alias)s.ref = ''
                    THEN %(partner_alias)s.id::text
                    ELSE replace(%(partner_alias)s.ref, '|', '/')
                    END
                ELSE ''
                END
                AS CompAuxNum,
                CASE WHEN %(account_alias)s.account_type IN
                    ('asset_receivable', 'liability_payable')
                     THEN COALESCE(REGEXP_REPLACE(replace(
                         %(partner_alias)s.name, '|', '/'),
                         '[\\t\\r\\n]', ' ', 'g'), '')
                     ELSE ''
                END AS CompAuxLib,
                CASE
                    WHEN MIN(%(move_alias)s.ref) IS null OR
                        MIN(%(move_alias)s.ref) = ''
                        THEN '-'
                    ELSE REGEXP_REPLACE(
                        replace(
                            MIN(%(move_alias)s.ref),
                            '|',
                            '/'
                        ), '[\\t\\r\\n]', ' ', 'g')
                    END AS PieceRef,
                TO_CHAR(MAX(COALESCE(
                    %(move_alias)s.invoice_date,
                    %(move_alias)s.date)),
                    'YYYYMMDD'
                ) AS PieceDate,
                CASE
                    WHEN MIN(account_move_line.name) IS NULL
                        OR MIN(account_move_line.name) = ''
                        THEN '/'
                    WHEN MIN(account_move_line.name) SIMILAR TO '[\\t|\\s|\\n]*'
                        THEN '/'
                    ELSE REGEXP_REPLACE(replace(
                        MIN(account_move_line.name),
                        '|',
                        '/'), '[\\t\\n\\r]', ' ', 'g')
                    END AS EcritureLib,
                replace(
                    CASE
                        WHEN SUM(account_move_line.debit) = 0
                        THEN '0,00'
                        ELSE TO_CHAR(
                            SUM(account_move_line.debit),
                            '000000000000000D99'
                        )
                        END, '.', ',') AS Debit,
                replace(
                    CASE
                        WHEN SUM(account_move_line.credit) = 0
                        THEN '0,00'
                        ELSE TO_CHAR(
                            SUM(account_move_line.credit),
                            '000000000000000D99'
                        )
                        END, '.', ',') AS Credit,
                CASE
                    WHEN MIN(%(full_alias)s.id) IS NULL
                    THEN ''::text
                    ELSE MIN(%(full_alias)s.id)::text
                    END AS EcritureLet,
                CASE
                    WHEN MIN(account_move_line.full_reconcile_id) IS NULL
                    THEN ''
                    ELSE TO_CHAR(MIN(%(full_alias)s.create_date), 'YYYYMMDD')
                    END AS DateLet,
                TO_CHAR(MIN(%(move_alias)s.date), 'YYYYMMDD') AS ValidDate,
                CASE
                    WHEN
                        SUM(account_move_line.amount_currency) IS NULL OR
                        SUM(account_move_line.amount_currency) = 0
                    THEN ''
                    ELSE replace(
                        TO_CHAR(
                            SUM(account_move_line.amount_currency),
                            '000000000000000D99'
                        ),
                        '.',
                        ','
                    ) END AS Montantdevise,
                CASE
                    WHEN MIN(account_move_line.currency_id) IS NULL
                    THEN ''
                    ELSE MIN(%(currency_alias)s.name)
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
            account_alias=SQL.identifier(kwargs.get("account_alias")),
            aj_name=kwargs.get("aj_name"),
            aa_code=kwargs.get("aa_code"),
            aa_name=kwargs.get("aa_name"),
        )
        return columns

    def _get_rows_fec_lines_group_sale_purchase(self):
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
                ("journal_id.type", "not in", ["sale", "purchase"]),
            ],
            limit=query_limit + 1,
            order="date, move_name, id",
        )
        account_alias = query.join(
            "account_move_line", "account_id", "account_account", "id", "account_id"
        )
        params = {
            "account_alias": account_alias,
            "aa_name": self.env["account.account"]._field_to_sql(
                account_alias,
                "name",
            ),
            "aa_code": self.env["account.account"]._field_to_sql(
                account_alias, "code", query
            ),
            "aj_name": self.env["account.journal"]._field_to_sql(
                "account_move_line__journal_id", "name"
            ),
        }
        columns = self._sql_query_fec_lines(query, **params)

        query2 = self.env["account.move.line"]._search(
            domain=self._get_base_domain()
            + [
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
                ("journal_id.type", "in", ["sale", "purchase"]),
            ],
            limit=query_limit + 1,
            order="date,move_name,id",
        )
        account_alias2 = query2.join(
            "account_move_line", "account_id", "account_account", "id", "account_id"
        )
        params2 = {
            "account_alias": account_alias2,
            "aa_name": self.env["account.account"]._field_to_sql(
                account_alias2,
                "name",
            ),
            "aa_code": self.env["account.account"]._field_to_sql(
                account_alias2, "code", query2
            ),
            "aj_name": self.env["account.journal"]._field_to_sql(
                "account_move_line__journal_id", "name"
            ),
        }
        columns2 = self._sql_query_fec_lines2(query2, **params2)
        query2.groupby = SQL("""
            account_move_line__move_id.name,
            account_move_line__account_id.id,
            account_move_line__partner_id.id
        """)
        query2.order = SQL("""
            MIN(account_move_line.date),
            MIN(account_move_line.move_name),
            MIN(account_move_line.id)
        """)

        sql_query = SQL(
            """
                (%s)
                UNION
                (%s)
                ORDER BY PieceDate, EcritureNum
            """,
            query.select(columns),
            query2.select(columns2),
        )
        rows_to_write = []
        self._cr.execute(sql_query)
        query_results = self._cr.fetchall()
        rows_to_write.append(query_results[:query_limit])
        return rows_to_write

    def generate_fec(self):
        if not self.group_sale_purchase:
            return super().generate_fec()
        if self.date_from > self.date_to:
            raise UserError(self.env._("The start date must be before the end date."))

        company = self.company_id
        siren = self._get_siren(company)

        header = [
            "JournalCode",  # 0
            "JournalLib",  # 1
            "EcritureNum",  # 2
            "EcritureDate",  # 3
            "CompteNum",  # 4
            "CompteLib",  # 5
            "CompAuxNum",  # 6  We use partner.id
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
        # INITIAL BALANCE
        unaffected_earnings_account = self.env["account.account"].search(
            [
                *self.env["account.account"]._check_company_domain(company),
                ("account_type", "=", "equity_unaffected"),
            ],
            limit=1,
        )
        # used to make sure that we add
        # the unaffected earning initial balance only once
        unaffected_earnings_line = True
        if unaffected_earnings_account:
            # compute the benefit/loss of last year to
            # add in the initial balance of the current year earnings account
            unaffected_earnings_results = self._do_query_unaffected_earnings()
            unaffected_earnings_line = False

        aa_name = self.env["account.account"]._field_to_sql(
            "account_move_line__account_id", "name"
        )

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
                replace(CASE WHEN sum(account_move_line.balance) <= 0
                    THEN '0,00' ELSE to_char(SUM(account_move_line.balance),
                        '000000000000000D99')
                    END, '.', ',')
                AS Debit,
                replace(CASE WHEN sum(account_move_line.balance) >= 0
                    THEN '0,00' ELSE to_char(-SUM(account_move_line.balance),
                    '000000000000000D99')
                    END, '.', ',')
                AS Credit,
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
        self._cr.execute(SQL("%s GROUP BY account_move_line__account_id.id", sql_query))

        currency_digits = 2
        for row in self._cr.fetchall():
            listrow = list(row)
            account_id = listrow.pop()
            if not unaffected_earnings_line:
                account = self.env["account.account"].browse(account_id)
                if account.account_type == "equity_unaffected":
                    # add the benefit/loss of previous fiscal year
                    # to the first unaffected earnings account found.
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

        # if the unaffected earnings account
        # wasn't in the selection yet: add it manually
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
                [("account_type", "=", "equity_unaffected")], limit=1
            )
            if unaffected_earnings_account:
                unaffected_earnings_results[4] = unaffected_earnings_account.code
                unaffected_earnings_results[5] = unaffected_earnings_account.name
            rows_to_write.append(unaffected_earnings_results)

        # INITIAL BALANCE - receivable/payable
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
                COALESCE(NULLIF(
                    replace(account_move_line__partner_id.ref, '|', '/'), ''),
                    account_move_line__partner_id.id::text)
                AS CompAuxNum,
                COALESCE(replace(account_move_line__partner_id.name, '|', '/'),
                    '')
                AS CompAuxLib,
                '-' AS PieceRef,
                %(formatted_date_from)s AS PieceDate,
                '/' AS EcritureLib,
                replace(CASE WHEN sum(account_move_line.balance) <= 0
                    THEN '0,00'
                    ELSE to_char(SUM(account_move_line.balance),
                    '000000000000000D99')
                    END, '.', ',')
                AS Debit,
                replace(CASE WHEN sum(account_move_line.balance) >= 0
                    THEN '0,00'
                    ELSE to_char(-SUM(account_move_line.balance),
                    '000000000000000D99')
                    END, '.', ',')
                AS Credit,
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
        self._cr.execute(
            SQL(
                """%s GROUP BY account_move_line__partner_id.id,
                account_move_line__account_id.id""",
                sql_query,
            )
        )

        for row in self._cr.fetchall():
            listrow = list(row)
            listrow.pop()
            rows_to_write.append(listrow)

        # LINES
        fec_lines = self._get_rows_fec_lines_group_sale_purchase()
        with io.StringIO() as fecfile:
            csv_writer = csv.writer(fecfile, delimiter="|", lineterminator="\r\n")

            # Write header and initial balances
            csv_writer.writerows(rows_to_write)

            # Write current period's data
            for query_result in fec_lines:
                csv_writer.writerows(query_result)

            content = fecfile.getvalue()[:-2].encode(self.encoding, errors="replace")

        end_date = fields.Date.to_string(self.date_to).replace("-", "")
        suffix = ""
        if self.export_type == "nonofficial":
            suffix = "-NONOFFICIAL"

        # Set fiscal year lock date to the end date (not in test)
        fiscalyear_lock_date = company.fiscalyear_lock_date
        if (
            self.update_fiscalyear_lock_date
            and self.export_type == "official"
            and (not fiscalyear_lock_date or fiscalyear_lock_date < self.date_to)
        ):
            company.write({"fiscalyear_lock_date": self.date_to})
        filename = f"{siren}FEC{end_date}{suffix}.csv"
        self.write(
            {
                "filename": filename,
                "fec_data": base64.encodebytes(content),
            }
        )
        action = {
            "name": "FEC",
            "type": "ir.actions.act_url",
            "url": f"web/content/?model={self._name}&id={self.id}&filename_field="
            f"filename&field=fec_data&download=true&filename={self.filename}",
            "target": "new",
        }
        return action
