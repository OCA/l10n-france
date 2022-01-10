from odoo import models, fields, api
from odoo.tools import float_is_zero

import base64


class AccountFrFec(models.TransientModel):
    _inherit = 'account.fr.fec'

    group_sale_purchase = fields.Boolean(
        'Group Sale and Purchase Journals',
        default=True
    )

    @api.multi
    def generate_fec(self):
        if not self.group_sale_purchase:
            return super(AccountFrFec, self).generate_fec()
        self.ensure_one()
        # We choose to implement the flat file instead of the XML
        # file for 2 reasons :
        # 1) the XSD file impose to have the label on the account.move
        # but Odoo has the label on the account.move.line, so that's a
        # problem !
        # 2) CSV files are easier to read/use for a regular accountant.
        # So it will be easier for the accountant to check the file before
        # sending it to the fiscal administration
        company = self.env.user.company_id
        company_legal_data = self._get_company_legal_data(company)

        header = [
            u'JournalCode',     # 0
            u'JournalLib',      # 1
            u'EcritureNum',     # 2
            u'EcritureDate',    # 3
            u'CompteNum',       # 4
            u'CompteLib',       # 5
            u'CompAuxNum',      # 6  We use partner.id
            u'CompAuxLib',      # 7
            u'PieceRef',        # 8
            u'PieceDate',       # 9
            u'EcritureLib',     # 10
            u'Debit',           # 11
            u'Credit',          # 12
            u'EcritureLet',     # 13
            u'DateLet',         # 14
            u'ValidDate',       # 15
            u'Montantdevise',   # 16
            u'Idevise',         # 17
        ]

        rows_to_write = [header]
        # INITIAL BALANCE
        unaffected_earnings_xml_ref = self.env.ref(
            'account.data_unaffected_earnings')
        # used to make sure that we add the unaffected earning
        # initial balance only once
        unaffected_earnings_line = True
        if unaffected_earnings_xml_ref:
            # compute the benefit/loss of last year to add in the initial
            # balance of the current year earnings account
            unaffected_earnings_results = self._do_query_unaffected_earnings()
            unaffected_earnings_line = False

        sql_query = '''
        SELECT
            'OUV' AS JournalCode,
            'Balance initiale' AS JournalLib,
            'OUVERTURE/' || %s AS EcritureNum,
            %s AS EcritureDate,
            MIN(aa.code) AS CompteNum,
            replace(replace(MIN(aa.name), '|', '/'), '\t', '') AS CompteLib,
            '' AS CompAuxNum,
            '' AS CompAuxLib,
            '-' AS PieceRef,
            %s AS PieceDate,
            '/' AS EcritureLib,
            replace(CASE WHEN sum(aml.balance) <= 0 THEN '0,00'
            ELSE to_char(SUM(aml.balance), '000000000000000D99')
            END, '.', ',') AS Debit,
            replace(CASE WHEN sum(aml.balance) >= 0 THEN '0,00'
            ELSE to_char(-SUM(aml.balance), '000000000000000D99')
            END, '.', ',') AS Credit,
            '' AS EcritureLet,
            '' AS DateLet,
            %s AS ValidDate,
            '' AS Montantdevise,
            '' AS Idevise,
            MIN(aa.id) AS CompteID
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id=aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
            LEFT JOIN account_account_type aat ON aa.user_type_id = aat.id
        WHERE
            am.date < %s
            AND am.company_id = %s
            AND aat.include_initial_balance = 't'
            AND (aml.debit != 0 OR aml.credit != 0)
        '''

        # For official report: only use posted entries
        if self.export_type == "official":
            sql_query += '''
            AND am.state = 'posted'
            '''

        sql_query += '''
        GROUP BY aml.account_id, aat.type
        HAVING round(sum(aml.balance), %s) != 0
        AND aat.type not in ('receivable', 'payable')
        '''
        formatted_date_from = fields.Date.to_string(
            self.date_from).replace('-', '')
        date_from = self.date_from
        formatted_date_year = date_from.year
        currency_digits = 2

        self._cr.execute(
            sql_query, (
                formatted_date_year, formatted_date_from, formatted_date_from,
                formatted_date_from, self.date_from, company.id,
                currency_digits))

        for row in self._cr.fetchall():
            listrow = list(row)
            account_id = listrow.pop()
            if not unaffected_earnings_line:
                account = self.env['account.account'].browse(account_id)
                if account.user_type_id.id == self.env.ref(
                        'account.data_unaffected_earnings').id:
                    # add the benefit/loss of previous fiscal year
                    # to the first unaffected earnings account found.
                    unaffected_earnings_line = True
                    current_amount = float(
                        listrow[11].replace(',', '.')) - float(
                        listrow[12].replace(',', '.'))
                    unaffected_earnings_amount = \
                        float(unaffected_earnings_results[11].replace(',', '.')
                              ) - \
                        float(unaffected_earnings_results[12].replace(',', '.')
                              )
                    listrow_amount = current_amount + \
                        unaffected_earnings_amount
                    if float_is_zero(listrow_amount,
                                     precision_digits=currency_digits):
                        continue
                    if listrow_amount > 0:
                        listrow[11] = str(listrow_amount).replace('.', ',')
                        listrow[12] = '0,00'
                    else:
                        listrow[11] = '0,00'
                        listrow[12] = str(-listrow_amount).replace('.', ',')
            rows_to_write.append(listrow)

        # if the unaffected earnings account wasn't in the selection yet: add
        # it manually
        if (not unaffected_earnings_line
            and unaffected_earnings_results
            and (unaffected_earnings_results[11] != '0,00'
                 or unaffected_earnings_results[12] != '0,00')):
            # search an unaffected earnings account
            unaffected_earnings_account = self.env['account.account'].search(
                [(
                    'user_type_id',
                    '=',
                    self.env.ref('account.data_unaffected_earnings').id),
                 ], limit=1)
            if unaffected_earnings_account:
                unaffected_earnings_results[
                    4] = unaffected_earnings_account.code
                unaffected_earnings_results[
                    5] = unaffected_earnings_account.name
            rows_to_write.append(unaffected_earnings_results)

        # INITIAL BALANCE - receivable/payable
        sql_query = '''
        SELECT
            'OUV' AS JournalCode,
            'Balance initiale' AS JournalLib,
            'OUVERTURE/' || %s AS EcritureNum,
            %s AS EcritureDate,
            MIN(aa.code) AS CompteNum,
            replace(MIN(aa.name), '|', '/') AS CompteLib,
            CASE WHEN rp.ref IS null OR rp.ref = ''
            THEN COALESCE('ID ' || rp.id, '')
            ELSE replace(rp.ref, '|', '/')
            END
            AS CompAuxNum,
            COALESCE(replace(rp.name, '|', '/'), '') AS CompAuxLib,
            '-' AS PieceRef,
            %s AS PieceDate,
            '/' AS EcritureLib,
            replace(CASE WHEN sum(aml.balance) <= 0 THEN '0,00'
            ELSE to_char(SUM(aml.balance), '000000000000000D99')
            END, '.', ',') AS Debit,
            replace(CASE WHEN sum(aml.balance) >= 0 THEN '0,00'
            ELSE to_char(-SUM(aml.balance), '000000000000000D99')
            END, '.', ',') AS Credit,
            '' AS EcritureLet,
            '' AS DateLet,
            %s AS ValidDate,
            '' AS Montantdevise,
            '' AS Idevise,
            MIN(aa.id) AS CompteID
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id=aml.move_id
            LEFT JOIN res_partner rp ON rp.id=aml.partner_id
            JOIN account_account aa ON aa.id = aml.account_id
            LEFT JOIN account_account_type aat ON aa.user_type_id = aat.id
        WHERE
            am.date < %s
            AND am.company_id = %s
            AND aat.include_initial_balance = 't'
            AND (aml.debit != 0 OR aml.credit != 0)
        '''

        # For official report: only use posted entries
        if self.export_type == "official":
            sql_query += '''
            AND am.state = 'posted'
            '''

        sql_query += '''
        GROUP BY aml.account_id, aat.type, rp.ref, rp.id
        HAVING round(sum(aml.balance), %s) != 0
        AND aat.type in ('receivable', 'payable')
        '''
        self._cr.execute(
            sql_query, (
                formatted_date_year, formatted_date_from, formatted_date_from,
                formatted_date_from, self.date_from, company.id,
                currency_digits))

        for row in self._cr.fetchall():
            listrow = list(row)
            account_id = listrow.pop()
            rows_to_write.append(listrow)

        # LINES
        sql_query = self.write_fec_lines()
        self._cr.execute(
            sql_query, (self.date_from, self.date_to, company.id,
                        self.date_from, self.date_to, company.id))

        for row in self._cr.fetchall():
            rows_to_write.append(list(row))

        fecvalue = self._csv_write_rows(rows_to_write)
        end_date = fields.Date.to_string(self.date_to).replace('-', '')
        suffix = ''
        if self.export_type == "nonofficial":
            suffix = '-NONOFFICIAL'

        self.write({
            'fec_data': base64.encodestring(fecvalue),
            # Filename = <siren>FECYYYYMMDD where YYYMMDD is the closing date
            'filename': '%sFEC%s%s.csv' % (company_legal_data['siren'],
                                           end_date, suffix),
        })

        url = "&filename_field=filename&field=fec_data&download=true&filename="
        action = {
            'name': 'FEC',
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=account.fr.fec&id=" + str(self.id)
                   + url + self.filename,
            'target': 'self',
        }
        return action

    @api.multi
    def write_fec_lines(self):
        sql_query = r'''
                (SELECT
                    replace(aj.code, '|', '/') AS JournalCode,
                    replace(aj.name, '|', '/') AS JournalLib,
                    replace(am.name, '|', '/') AS EcritureNum,
                    TO_CHAR(am.date, 'YYYYMMDD') AS EcritureDate,
                    aa.code AS CompteNum,
                    replace(aa.name, '|', '/') AS CompteLib,
                    CASE WHEN rp.ref IS null OR rp.ref = ''
                    THEN COALESCE('ID ' || rp.id, '')
                    ELSE rp.ref
                    END
                    AS CompAuxNum,
                    COALESCE(replace(rp.name, '|', '/'), '') AS CompAuxLib,
                    CASE WHEN am.ref IS null OR am.ref = ''
                    THEN '-'
                    ELSE replace(am.ref, '|', '/')
                    END
                    AS PieceRef,
                    TO_CHAR(am.date, 'YYYYMMDD') AS PieceDate,
                    CASE WHEN aml.name IS NULL THEN '/'
                        WHEN aml.name SIMILAR TO '[\t|\s|\n]*' THEN '/'
                        ELSE replace(aml.name, '|', '/') END AS EcritureLib,
                    replace(CASE WHEN aml.debit = 0 THEN '0,00' ELSE
                    to_char(aml.debit, '000000000000000D99') END, '.', ',')
                    AS Debit,
                    replace(CASE WHEN aml.credit = 0 THEN '0,00' ELSE
                    to_char(aml.credit, '000000000000000D99') END, '.', ',')
                    AS Credit,
                    CASE WHEN rec.name IS NULL THEN '' ELSE rec.name
                    END AS EcritureLet,
                    CASE WHEN aml.full_reconcile_id IS NULL THEN '' ELSE
                    TO_CHAR(rec.create_date, 'YYYYMMDD') END AS DateLet,
                    TO_CHAR(am.date, 'YYYYMMDD') AS ValidDate,
                    CASE
                        WHEN aml.amount_currency IS NULL OR
                        aml.amount_currency = 0 THEN ''
                        ELSE replace(to_char(aml.amount_currency,
                                            '000000000000000D99'), '.', ',')
                    END AS Montantdevise,
                    CASE WHEN aml.currency_id IS NULL THEN '' ELSE rc.name END
                    AS Idevise,
                    TO_CHAR(aml.account_id, '0'),
                    TO_CHAR(aml.partner_id, '0')
                FROM
                    account_move_line aml
                    LEFT JOIN account_move am ON am.id=aml.move_id
                    LEFT JOIN res_partner rp ON rp.id=aml.partner_id
                    JOIN account_journal aj ON aj.id = am.journal_id
                    JOIN account_account aa ON aa.id = aml.account_id
                    LEFT JOIN res_currency rc ON rc.id = aml.currency_id
                    LEFT JOIN account_full_reconcile rec ON
                                rec.id = aml.full_reconcile_id
                WHERE
                    am.date >= %s
                    AND aj.type not in ('sale', 'purchase')
                    AND am.date <= %s
                    AND am.company_id = %s
                    AND (aml.debit != 0 OR aml.credit != 0)
                '''

        # For official report: only use posted entries
        if self.export_type == "official":
            sql_query += '''
                    AND am.state = 'posted'
                    '''

        sql_query += '''
                ORDER BY
                    am.date,
                    am.name,
                    aml.id)
                '''

        sql_query2 = r'''
                SELECT
                    replace(STRING_AGG(distinct aj.code, ';'), '|', '/') AS
                    JournalCode,
                    replace(STRING_AGG(distinct aj.name, ';'), '|', '/')
                    AS JournalLib,
                    replace(am.name, '|', '/') AS EcritureNum,
                    TO_CHAR(MAX(am.date), 'YYYYMMDD') AS
                    EcritureDate,
                    STRING_AGG(distinct aa.code, ';') AS CompteNum,
                    replace(STRING_AGG(distinct aa.name, ';'), '|', '/')
                    AS CompteLib,
                    CASE WHEN MIN(rp.ref) IS null OR MIN(rp.ref) = ''
                    THEN COALESCE('ID ' || min(rp.id), '')
                    ELSE MIN(rp.ref)
                    END
                    AS CompAuxNum,
                    COALESCE(replace(MAX(rp.name), '|', '/'), '') AS
                    CompAuxLib,
                    CASE WHEN MIN(am.ref) IS null OR MIN(am.ref) = ''
                    THEN '-'
                    ELSE replace(MIN(am.ref), '|', '/')
                    END
                    AS PieceRef,
                    TO_CHAR(MAX(am.date), 'YYYYMMDD') AS PieceDate,
                    CASE WHEN MIN(aml.name) IS NULL THEN '/'
                        WHEN MIN(aml.name) SIMILAR TO '[\t|\s|\n]*' THEN '/'
                        ELSE replace(MAX(aml.name), '|', '/') END AS
                        EcritureLib,
                    replace(
                        CASE WHEN
                            sum(aml.debit) = 0 THEN '0,00'
                        ELSE
                            to_char(sum(aml.debit), '000000000000000D99')
                        END, '.', ',') AS Debit,
                    replace(CASE WHEN sum(aml.credit) = 0 THEN '0,00' ELSE
                    to_char(sum(aml.credit), '000000000000000D99')
                                END, '.', ',') AS Credit,
                    CASE WHEN MIN(rec.name) IS NULL THEN '' ELSE MIN(rec.name)
                    END AS EcritureLet,
                    CASE WHEN MIN(aml.full_reconcile_id) IS NULL THEN '' ELSE
                    TO_CHAR(MIN(rec.create_date), 'YYYYMMDD') END AS DateLet,
                    TO_CHAR(MIN(am.date), 'YYYYMMDD') AS ValidDate,
                    CASE
                        WHEN MIN(aml.amount_currency) IS NULL OR
                        MIN(aml.amount_currency) = 0 THEN ''
                        ELSE replace(to_char(MIN(aml.amount_currency),
                        '000000000000000D99'), '.', ',')
                    END AS Montantdevise,
                    CASE WHEN MIN(aml.currency_id) IS NULL THEN '' ELSE
                    MIN(rc.name) END AS Idevise,
                    TO_CHAR(aml.account_id, '0'),
                    TO_CHAR(aml.partner_id, '0')
                FROM
                    account_move_line aml
                    LEFT JOIN account_move am ON am.id=aml.move_id
                    LEFT JOIN res_partner rp ON rp.id=aml.partner_id
                    JOIN account_journal aj ON aj.id = am.journal_id
                    JOIN account_account aa ON aa.id = aml.account_id
                    LEFT JOIN res_currency rc ON rc.id = aml.currency_id
                    LEFT JOIN account_full_reconcile rec ON
                    rec.id = aml.full_reconcile_id
                WHERE
                    am.date >= %s
                    AND aj.type in ('sale', 'purchase')
                    AND am.date <= %s
                    AND am.company_id = %s
                    AND (aml.debit != 0 OR aml.credit != 0)
                '''

        # For official report: only use posted entries
        if self.export_type == "official":
            sql_query2 += '''
                    AND am.state = 'posted'
                    '''

        sql_query2 += '''
                GROUP BY
                    am.name,
                    aml.account_id,
                    aml.partner_id
                     '''
        sql_query2 += '''
                ORDER BY
                    MIN(am.date),
                    MIN(am.name),
                    MIN(aml.id)
                '''

        sql_query = sql_query + '''
                UNION (
                    ''' + sql_query2 + ''' )
                ORDER BY
                    PieceDate,
                    EcritureNum
                    '''
        return sql_query
