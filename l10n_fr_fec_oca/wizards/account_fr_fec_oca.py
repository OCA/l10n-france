# Copyright 2016-2025 Odoo SA (https://www.odoo.com/fr_FR/)
# Copyright 2013-2025 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>

# This code is taken from the module l10n_fr_account of the official addons
# The model has been renamed from l10n_fr.fec.export.wizard to l10n.fr.fec.oca
# and then several improvements has been made (a large part of these improvements
# cannot be done via an inherit of the native code)

# TODO restore option partner_identifier from v16
# and improve it by introducing an option to have
# payable-specific prefix and receivable-specific prefix

import base64
import csv
import io
from odoo.tools import float_is_zero, SQL
from odoo import fields, models, api
from odoo.exceptions import UserError
from stdnum.fr.siren import is_valid as siren_is_valid


class AccountFrFecOca(models.TransientModel):
    _name = 'account.fr.fec.oca'
    _description = 'Fichier Echange Informatise'

    company_id = fields.Many2one(
        "res.company",
        ondelete="cascade",
        required=True,
        default=lambda self: self.env.company,
    )
    date_range_id = fields.Many2one("date.range")
    date_from = fields.Date(
        string='Start Date',
        compute="_compute_dates",
        required=True,
        readonly=False,
        store=True,
        )
    date_to = fields.Date(
        string='End Date',
        compute="_compute_dates",
        required=True,
        readonly=False,
        store=True,
        )
    encoding = fields.Selection(
        [
            ("iso8859_15", "ISO-8859-15"),
            ("utf-8", "UTF-8"),
        ],
        default="iso8859_15",
        required=True,
    )

    filename = fields.Char(readonly=True)
    fec_data = fields.Binary("FEC File", readonly=True, attachment=True)
    update_fiscalyear_lock_date = fields.Boolean(
        string="Update Global Lock Date",
        help="If enabled, Odoo will update the global lock date after generation of the FEC file.")
    exclude_zero = fields.Boolean(string="Exclude lines at 0", default=True)
    export_type = fields.Selection([
        ('official', 'Official FEC report (posted entries only)'),
        ('nonofficial', 'Non-official FEC report (posted and draft entries)'),
    ], string='Export Type', required=True, default='official')
    excluded_journal_ids = fields.Many2many('account.journal', string="Excluded Journals",
                                            domain="[('company_id', 'parent_of', company_id)]")

    @api.depends("date_range_id")
    def _compute_dates(self):
        for wiz in self:
            if wiz.date_range_id:
                wiz.date_from = wiz.date_range_id.date_start
                wiz.date_to = wiz.date_range_id.date_end

    def _get_base_domain(self):
        domain = [('company_id', 'in', tuple(self.company_id._accessible_branches().ids))]
        # For official report: only use posted entries
        if self.export_type == "official":
            domain.append(('parent_state', '=', 'posted'))
        else:
            domain.append(('parent_state', 'in', ('posted', 'draft')))
        if self.excluded_journal_ids:
            domain.append(('journal_id', 'not in', self.excluded_journal_ids.ids))
        if self.exclude_zero:
            domain.append(('balance', '!=', 0.0))
        return domain

    def _do_query_unaffected_earnings(self):
        """ Compute the sum of ending balances for all accounts that are of a type that does not bring forward the balance in new fiscal years.
            This is needed because we have to display only one line for the initial balance of all expense/revenue accounts in the FEC.
        """
        query = self.env['account.move.line']._search(self._get_base_domain() + [
            ('date', '<', self.date_from),
            ('account_id.include_initial_balance', '=', False),
        ])
        sql_query = query.select(SQL(
            """
                'OUV' AS JournalCode,
                'Balance initiale' AS JournalLib,
                'OUVERTURE/' || %(formatted_date_year)s AS EcritureNum,
                %(formatted_date_from)s AS EcritureDate,
                '120/129' AS CompteNum,
                'Benefice (perte) reporte(e)' AS CompteLib,
                '' AS CompAuxNum,
                '' AS CompAuxLib,
                '-' AS PieceRef,
                %(formatted_date_from)s AS PieceDate,
                '/' AS EcritureLib,
                replace(CASE WHEN COALESCE(sum(account_move_line.balance), 0) <= 0 THEN '0,00' ELSE to_char(SUM(account_move_line.balance), '000000000000000D99') END, '.', ',') AS Debit,
                replace(CASE WHEN COALESCE(sum(account_move_line.balance), 0) >= 0 THEN '0,00' ELSE to_char(-SUM(account_move_line.balance), '000000000000000D99') END, '.', ',') AS Credit,
                '' AS EcritureLet,
                '' AS DateLet,
                %(formatted_date_from)s AS ValidDate,
                '' AS Montantdevise,
                '' AS Idevise
            """,
            formatted_date_year=self.date_from.year,
            formatted_date_from=fields.Date.to_string(self.date_from).replace('-', ''),
        ))
        self.env.flush_all()
        self._cr.execute(sql_query)
        return list(self._cr.fetchone())

    def _get_siren(self, company):
        # Get SIREN from SIRET and not from VAT
        # so that it also work on companies that are not subject to VAT
        if not company.siret:
            raise UserError(self.env._("Missing SIRET on company %s.", company.display_name))
        siren = company.siret[:9]
        if not siren_is_valid(siren):
            raise UserError(self.env._(
                "SIREN '%(siren)s' of company %(company)s is invalid.",
                siren=siren,
                company=company.display_name))
        return siren

    def generate_fec(self):
        # We choose to implement the flat file instead of the XML file for 2 reasons :
        # 1) the XSD file impose to have the label on the account.move, but Odoo has the label on the account.move.line,
        # so that's a  problem !
        # 2) CSV files are easier to read/use for a regular accountant. So it will be easier for the accountant to check
        # the file before sending it to the fiscal administration
        if self.date_from >= self.date_to:
            raise UserError(self.env._("The start date must be before the end date."))

        company = self.company_id
        siren = self._get_siren(company)

        header = [
            'JournalCode',    # 0
            'JournalLib',     # 1
            'EcritureNum',    # 2
            'EcritureDate',   # 3
            'CompteNum',      # 4
            'CompteLib',      # 5
            'CompAuxNum',     # 6  We use partner.id
            'CompAuxLib',     # 7
            'PieceRef',       # 8
            'PieceDate',      # 9
            'EcritureLib',    # 10
            'Debit',          # 11
            'Credit',         # 12
            'EcritureLet',    # 13
            'DateLet',        # 14
            'ValidDate',      # 15
            'Montantdevise',  # 16
            'Idevise',        # 17
            ]

        rows_to_write = [header]
        # INITIAL BALANCE
        unaffected_earnings_account = self.env['account.account'].search([
            *self.env['account.account']._check_company_domain(company),
            ('account_type', '=', 'equity_unaffected'),
        ], limit=1)
        unaffected_earnings_line = True  # used to make sure that we add the unaffected earning initial balance only once
        if unaffected_earnings_account:
            #compute the benefit/loss of last year to add in the initial balance of the current year earnings account
            unaffected_earnings_results = self._do_query_unaffected_earnings()
            unaffected_earnings_line = False

        aa_name = self.env['account.account']._field_to_sql('account_move_line__account_id', 'name')

        query = self.env['account.move.line']._search(self._get_base_domain() + [
            ('date', '<', self.date_from),
            ('account_id.include_initial_balance', '=', True),
            ('account_id.account_type', 'not in', ['asset_receivable', 'liability_payable']),
        ])
        aa_code = self.env['account.account']._field_to_sql('account_move_line__account_id', 'code', query)
        sql_query = query.select(SQL(
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
                replace(CASE WHEN sum(account_move_line.balance) <= 0 THEN '0,00' ELSE to_char(SUM(account_move_line.balance), '000000000000000D99') END, '.', ',') AS Debit,
                replace(CASE WHEN sum(account_move_line.balance) >= 0 THEN '0,00' ELSE to_char(-SUM(account_move_line.balance), '000000000000000D99') END, '.', ',') AS Credit,
                '' AS EcritureLet,
                '' AS DateLet,
                %(formatted_date_from)s AS ValidDate,
                '' AS Montantdevise,
                '' AS Idevise,
                MIN(account_move_line__account_id.id) AS CompteID
            """,
            formatted_date_year=self.date_from.year,
            formatted_date_from=fields.Date.to_string(self.date_from).replace('-', ''),
            aa_code=aa_code,
            aa_name=aa_name,
        ))
        self._cr.execute(SQL('%s GROUP BY account_move_line__account_id.id', sql_query))

        currency_digits = 2
        for row in self._cr.fetchall():
            listrow = list(row)
            account_id = listrow.pop()
            if not unaffected_earnings_line:
                account = self.env['account.account'].browse(account_id)
                if account.account_type == 'equity_unaffected':
                    #add the benefit/loss of previous fiscal year to the first unaffected earnings account found.
                    unaffected_earnings_line = True
                    current_amount = float(listrow[11].replace(',', '.')) - float(listrow[12].replace(',', '.'))
                    unaffected_earnings_amount = float(unaffected_earnings_results[11].replace(',', '.')) - float(unaffected_earnings_results[12].replace(',', '.'))
                    listrow_amount = current_amount + unaffected_earnings_amount
                    if float_is_zero(listrow_amount, precision_digits=currency_digits):
                        continue
                    if listrow_amount > 0:
                        listrow[11] = str(listrow_amount).replace('.', ',')
                        listrow[12] = '0,00'
                    else:
                        listrow[11] = '0,00'
                        listrow[12] = str(-listrow_amount).replace('.', ',')
            rows_to_write.append(listrow)

        #if the unaffected earnings account wasn't in the selection yet: add it manually
        if (not unaffected_earnings_line
            and unaffected_earnings_results
            and (unaffected_earnings_results[11] != '0,00'
                 or unaffected_earnings_results[12] != '0,00')):
            #search an unaffected earnings account
            unaffected_earnings_account = self.env['account.account'].search([
                ('account_type', '=', 'equity_unaffected')
            ], limit=1)
            if unaffected_earnings_account:
                unaffected_earnings_results[4] = unaffected_earnings_account.code
                unaffected_earnings_results[5] = unaffected_earnings_account.name
            rows_to_write.append(unaffected_earnings_results)

        # INITIAL BALANCE - receivable/payable
        query = self.env['account.move.line']._search(self._get_base_domain() + [
            ('date', '<', self.date_from),
            ('account_id.include_initial_balance', '=', True),
            ('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']),
        ])
        query.left_join('account_move_line', 'partner_id', 'res_partner', 'id', 'partner_id')
        aa_code = self.env['account.account']._field_to_sql('account_move_line__account_id', 'code', query)
        sql_query = query.select(SQL(
            """
                'OUV' AS JournalCode,
                'Balance initiale' AS JournalLib,
                'OUVERTURE/' || %(formatted_date_year)s AS EcritureNum,
                %(formatted_date_from)s AS EcritureDate,
                MIN(%(aa_code)s) AS CompteNum,
                replace(MIN(%(aa_name)s), '|', '/') AS CompteLib,
                COALESCE(NULLIF(replace(account_move_line__partner_id.ref, '|', '/'), ''), account_move_line__partner_id.id::text) AS CompAuxNum,
                COALESCE(replace(account_move_line__partner_id.name, '|', '/'), '') AS CompAuxLib,
                '-' AS PieceRef,
                %(formatted_date_from)s AS PieceDate,
                '/' AS EcritureLib,
                replace(CASE WHEN sum(account_move_line.balance) <= 0 THEN '0,00' ELSE to_char(SUM(account_move_line.balance), '000000000000000D99') END, '.', ',') AS Debit,
                replace(CASE WHEN sum(account_move_line.balance) >= 0 THEN '0,00' ELSE to_char(-SUM(account_move_line.balance), '000000000000000D99') END, '.', ',') AS Credit,
                '' AS EcritureLet,
                '' AS DateLet,
                %(formatted_date_from)s AS ValidDate,
                '' AS Montantdevise,
                '' AS Idevise,
                MIN(account_move_line__account_id.id) AS CompteID
            """,
            formatted_date_year=self.date_from.year,
            formatted_date_from=fields.Date.to_string(self.date_from).replace('-', ''),
            aa_code=aa_code,
            aa_name=aa_name,
        ))
        self._cr.execute(SQL('%s GROUP BY account_move_line__partner_id.id, account_move_line__account_id.id', sql_query))

        for row in self._cr.fetchall():
            listrow = list(row)
            listrow.pop()
            rows_to_write.append(listrow)

        # LINES
        query_limit = int(self.env['ir.config_parameter'].sudo().get_param('l10n_fr_fec.batch_size', 500000)) # To prevent memory errors when fetching the results
        query = self.env['account.move.line']._search(
            domain=self._get_base_domain() + [
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
            ],
            limit=query_limit + 1,
            order='date, move_name, id',
        )
        account_alias = query.join('account_move_line', 'account_id', 'account_account', 'id', 'account_id')
        aa_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)

        aj_name = self.env['account.journal']._field_to_sql('account_move_line__journal_id', 'name')
        columns = SQL(
            """
                REGEXP_REPLACE(replace(%(journal_alias)s.code, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS JournalCode,
                REGEXP_REPLACE(replace(%(aj_name)s, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS JournalLib,
                REGEXP_REPLACE(replace(%(move_alias)s.name, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS EcritureNum,
                TO_CHAR(%(move_alias)s.date, 'YYYYMMDD') AS EcritureDate,
                %(aa_code)s AS CompteNum,
                REGEXP_REPLACE(replace(%(aa_name)s, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS CompteLib,
                CASE WHEN %(account_alias)s.account_type IN ('asset_receivable', 'liability_payable')
                THEN
                    CASE WHEN %(partner_alias)s.ref IS null OR %(partner_alias)s.ref = ''
                    THEN %(partner_alias)s.id::text
                    ELSE replace(%(partner_alias)s.ref, '|', '/')
                    END
                ELSE ''
                END
                AS CompAuxNum,
                CASE WHEN %(account_alias)s.account_type IN ('asset_receivable', 'liability_payable')
                     THEN COALESCE(REGEXP_REPLACE(replace(%(partner_alias)s.name, '|', '/'), '[\\t\\r\\n]', ' ', 'g'), '')
                     ELSE ''
                END AS CompAuxLib,
                CASE WHEN %(move_alias)s.ref IS null OR %(move_alias)s.ref = ''
                     THEN '-'
                     ELSE REGEXP_REPLACE(replace(%(move_alias)s.ref, '|', '/'), '[\\t\\r\\n]', ' ', 'g')
                END AS PieceRef,
                TO_CHAR(COALESCE(%(move_alias)s.invoice_date, %(move_alias)s.date), 'YYYYMMDD') AS PieceDate,
                CASE WHEN account_move_line.name IS NULL OR account_move_line.name = '' THEN '/'
                     WHEN account_move_line.name SIMILAR TO '[\\t|\\s|\\n]*' THEN '/'
                     ELSE REGEXP_REPLACE(replace(account_move_line.name, '|', '/'), '[\\t\\n\\r]', ' ', 'g') END AS EcritureLib,
                replace(CASE WHEN account_move_line.debit = 0 THEN '0,00' ELSE to_char(account_move_line.debit, '000000000000000D99') END, '.', ',') AS Debit,
                replace(CASE WHEN account_move_line.credit = 0 THEN '0,00' ELSE to_char(account_move_line.credit, '000000000000000D99') END, '.', ',') AS Credit,
                CASE WHEN %(full_alias)s.id IS NULL THEN ''::text ELSE %(full_alias)s.id::text END AS EcritureLet,
                CASE WHEN account_move_line.full_reconcile_id IS NULL THEN '' ELSE TO_CHAR(%(full_alias)s.create_date, 'YYYYMMDD') END AS DateLet,
                TO_CHAR(%(move_alias)s.date, 'YYYYMMDD') AS ValidDate,
                CASE
                    WHEN account_move_line.amount_currency IS NULL OR account_move_line.amount_currency = 0 THEN ''
                    ELSE replace(to_char(account_move_line.amount_currency, '000000000000000D99'), '.', ',')
                END AS Montantdevise,
                CASE WHEN account_move_line.currency_id IS NULL THEN '' ELSE %(currency_alias)s.name END AS Idevise
            """,
            currency_alias=SQL.identifier(query.left_join('account_move_line', 'currency_id', 'res_currency', 'id', 'currency_id')),
            full_alias=SQL.identifier(query.left_join('account_move_line', 'full_reconcile_id', 'account_full_reconcile', 'id', 'full_reconcile_id')),
            journal_alias=SQL.identifier(query.left_join('account_move_line', 'journal_id', 'account_journal', 'id', 'journal_id')),
            move_alias=SQL.identifier(query.left_join('account_move_line', 'move_id', 'account_move', 'id', 'move_id')),
            partner_alias=SQL.identifier(query.left_join('account_move_line', 'partner_id', 'res_partner', 'id', 'partner_id')),
            account_alias=SQL.identifier(account_alias),
            aj_name=aj_name,
            aa_code=aa_code,
            aa_name=aa_name,
        )
        with io.StringIO() as fecfile:
            csv_writer = csv.writer(fecfile, delimiter='|', lineterminator='\r\n')

            # Write header and initial balances
            csv_writer.writerows(rows_to_write)

            # Write current period's data
            has_more_results = True
            while has_more_results:
                self._cr.execute(query.select(columns))
                query.offset += query_limit
                has_more_results = self._cr.rowcount > query_limit # we load one more result than the limit to check if there is more
                query_results = self._cr.fetchall()
                csv_writer.writerows(query_results[:query_limit])
            content = fecfile.getvalue()[:-2].encode(self.encoding, errors="replace")

        end_date = fields.Date.to_string(self.date_to).replace('-', '')
        suffix = ''
        if self.export_type == "nonofficial":
            suffix = '-NONOFFICIAL'

        # Set fiscal year lock date to the end date (not in test)
        fiscalyear_lock_date = company.fiscalyear_lock_date
        if self.update_fiscalyear_lock_date and self.export_type == "official" and (not fiscalyear_lock_date or fiscalyear_lock_date < self.date_to):
            company.write({'fiscalyear_lock_date': self.date_to})
        filename = f"{siren}FEC{end_date}{suffix}.csv"
        self.write({
            'filename': filename,
            'fec_data': base64.encodebytes(content),
            })
        action = {
            "name": "FEC",
            "type": "ir.actions.act_url",
            "url": f"web/content/?model={self._name}&id={self.id}&filename_field=filename&"
            f"field=fec_data&download=true&filename={filename}",
            "target": "new",
            }
        return action
