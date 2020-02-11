# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
import csv
import os
import time
import base64
import StringIO

from openerp import models, fields, api, _
from openerp.exceptions import UserError

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.modules import get_module_resource

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession


class AccountFrFec(models.TransientModel):
    _inherit = 'account.fr.fec'

    @api.multi
    def export_fec_csv(self):
        self.ensure_one()
        return self.generate_fec()

    @api.multi
    def export_fec_txt(self):
        self.ensure_one()
        return self.generate_fec(extension="txt", delimiter='\t')

    @api.multi
    def export_fec_csv_background(self):
        self.ensure_one()
        return self.generate_fec_file_in_background()

    @api.multi
    def export_fec_txt_background(self):
        self.ensure_one()
        return self.generate_fec_file_in_background(
            extension="txt", delimiter='\t')

    @api.multi
    def generate_fec(self, extension="csv", delimiter='|'):
        self.ensure_one()
        fec_file = self.write_fec_header(extension, delimiter)
        file_name, fec_file = self.write_fec_lines(
            fec_file, delimiter, self.date_from, self.date_to, extension
        )
        fecvalue = fec_file.getvalue()
        self.write({
            'filename': file_name,
            'fec_data': base64.encodestring(fecvalue),
            })
        fec_file.close()
        return self.get_fec_file()

    @api.multi
    def create_attachment(self, delimiter, date_from, date_to, extension):
        self.ensure_one()
        # Write FEC header
        fec_file = self.write_fec_header(extension, delimiter)
        file_name, fec_file = self.write_fec_lines(
            fec_file, delimiter, date_from, date_to, extension
        )
        fecvalue = fec_file.getvalue()
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'datas_fname': file_name,
            'datas': base64.encodestring(fecvalue),
            })
        fec_file.close()
        email_template = self.env.ref(
            'l10n_fr_fec_custom.send_fec_file_mail_template')
        mail_id = email_template.send_mail(self.id)
        mail = self.env['mail.mail'].browse(mail_id)
        mail.write({'attachment_ids': [(4, attachment.id)]})
        mail.send()
        return True

    @api.multi
    def get_fec_file(self):
        self.ensure_one()
        return {
            'name': 'FEC',
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=account.fr.fec&id=" + str(self.id) +
                   "&filename_field=filename&field=fec_data&download=true"
                   "&filename=" + self.filename,
            'target': 'self',
        }

    @api.multi
    def write_fec_header(self, extension="csv", delimiter='|'):
        self.ensure_one()
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

        company = self.env.user.company_id
        if not company.vat:
            raise UserError(
                _("Missing VAT number for company %s") % company.name)
        if company.vat[0:2] != 'FR':
            raise UserError(
                _("FEC is for French companies only !"))

        siren = company.vat[4:13]
        end_date = self.date_to.replace('-', '')
        suffix = ''
        timestamp = int(time.mktime(datetime.now().timetuple()))
        if self.export_type == "nonofficial":
            suffix = '-NONOFFICIAL'
        file_name = '{}FEC{}{}_{}.{}'.format(
            siren, end_date, suffix, timestamp, extension)
        module = "l10n_fr_fec_custom"
        static_path = get_module_resource(module, "static")
        if not static_path:
            module_path = get_module_resource(module)
            os.mkdir("{}/static".format(module_path))
            static_path = get_module_resource(module, "static")
        file_path = '{}/{}'.format(static_path, file_name)
        fec_file = StringIO.StringIO()
        # fec_file = open(file_path, 'w')
        w = csv.writer(fec_file, delimiter=delimiter)
        w.writerow(header)

        # INITIAL BALANCE
        unaffected_earnings_xml_ref = self.env.ref(
            'account.data_unaffected_earnings')
        # used to make sure that we add the unaffected earning initial
        # balance only once
        unaffected_earnings_line = True
        if unaffected_earnings_xml_ref:
            # compute the benefit/loss of last year to add in the
            # initial balance of the current year earnings account
            unaffected_earnings_results = self.do_query_unaffected_earnings()
            unaffected_earnings_line = False

        sql_query = '''
        SELECT
            'OUV' AS JournalCode,
            'Balance initiale' AS JournalLib,
            'OUVERTURE/' || %s AS EcritureNum,
            %s AS EcritureDate,
            MIN(aa.code) AS CompteNum,
            replace(MIN(aa.name), '|', '/') AS CompteLib,
            '' AS CompAuxNum,
            '' AS CompAuxLib,
            '-' AS PieceRef,
            %s AS PieceDate,
            '/' AS EcritureLib,
            replace(CASE WHEN sum(aml.balance) <= 0 THEN '0,00' ELSE
            to_char(SUM(aml.balance), '000000000000000D99') END, '.', ',')
            AS Debit,
            replace(CASE WHEN sum(aml.balance) >= 0 THEN '0,00' ELSE
            to_char(-SUM(aml.balance), '000000000000000D99') END, '.', ',')
            AS Credit,
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
        HAVING sum(aml.balance) != 0
        AND aat.type not in ('receivable', 'payable')
        '''
        formatted_date_from = self.date_from.replace('-', '')
        date_from = datetime.strptime(self.date_from,
                                      DEFAULT_SERVER_DATE_FORMAT)
        formatted_date_year = date_from.year
        self._cr.execute(
            sql_query, (formatted_date_year, formatted_date_from,
                        formatted_date_from, formatted_date_from,
                        self.date_from, company.id))

        for row in self._cr.fetchall():
            listrow = list(row)
            account_id = listrow.pop()
            if not unaffected_earnings_line:
                account = self.env['account.account'].browse(account_id)
                if account.user_type_id.id == self.env.ref(
                        'account.data_unaffected_earnings').id:
                    # add the benefit/loss of previous fiscal year to the first
                    # unaffected earnings account found.
                    unaffected_earnings_line = True
                    current_amount = float(listrow[11].replace(',', '.')) - \
                        float(listrow[12].replace(',', '.'))
                    unaffected_earnings_amount = \
                        float(
                            unaffected_earnings_results[11].replace(',', '.'))\
                        - float(
                            unaffected_earnings_results[12].replace(',', '.'))
                    listrow_amount = current_amount + \
                        unaffected_earnings_amount
                    if listrow_amount > 0:
                        listrow[11] = str(listrow_amount).replace('.', ',')
                        listrow[12] = '0,00'
                    else:
                        listrow[11] = '0,00'
                        listrow[12] = str(-listrow_amount).replace('.', ',')
            w.writerow([s.encode("utf-8") for s in listrow])
        # if the unaffected earnings account wasn't in
        # the selection yet:  add it manually
        if (not unaffected_earnings_line
            and unaffected_earnings_results
            and (unaffected_earnings_results[11] != '0,00'
                 or unaffected_earnings_results[12] != '0,00')):
            # search an unaffected earnings account
            unaffected_earnings_account = self.env['account.account'].search(
                [('user_type_id', '=', self.env.ref(
                    'account.data_unaffected_earnings').id)], limit=1)
            if unaffected_earnings_account:
                unaffected_earnings_results[4] = \
                    unaffected_earnings_account.code
                unaffected_earnings_results[5] = \
                    unaffected_earnings_account.name
            w.writerow([s.encode("utf-8") for s in
                        unaffected_earnings_results])

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
            ELSE rp.ref
            END
            AS CompAuxNum,
            COALESCE(replace(rp.name, '|', '/'), '') AS CompAuxLib,
            '-' AS PieceRef,
            %s AS PieceDate,
            '/' AS EcritureLib,
            replace(CASE WHEN sum(aml.balance) <= 0 THEN '0,00' ELSE
            to_char(SUM(aml.balance), '000000000000000D99') END, '.', ',')
            AS Debit,
            replace(CASE WHEN sum(aml.balance) >= 0 THEN '0,00' ELSE
            to_char(-SUM(aml.balance), '000000000000000D99') END, '.', ',')
            AS Credit,
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
        HAVING sum(aml.balance) != 0
        AND aat.type in ('receivable', 'payable')
        '''
        self._cr.execute(
            sql_query, (
                formatted_date_year,
                formatted_date_from,
                formatted_date_from,
                formatted_date_from,
                self.date_from,
                company.id
            )
        )

        for row in self._cr.fetchall():
            listrow = list(row)
            account_id = listrow.pop()
            w.writerow([s.encode("utf-8") for s in listrow])

        # fec_file.close()
        # return file_path, file_name
        return fec_file

    @api.multi
    def generate_fec_file_in_background(self, extension="csv", delimiter='|'):
        self.ensure_one()
        # Prepare periods
        date_from = fields.Date.from_string(self.date_from)
        date_to = fields.Date.from_string(self.date_to)
        periods = self.prepare_periods(date_from, date_to)

        # Call job
        session = ConnectorSession(self._cr, self._uid)
        for priority, (period_from, period_to) in enumerate(periods, 10):
            # Create jobs
            period_from_str = fields.Date.to_string(period_from)
            period_to_str = fields.Date.to_string(period_to)
            write_fec_lines_session_job.delay(
                session, self._name, self.ids, period_from_str,
                period_to_str, delimiter, extension, priority=priority)
        return True

    @api.multi
    def prepare_periods(self, date_from, date_to):
        periods = []
        period_from = period_to = date_from
        while period_to < date_to:
            period_to = period_from + relativedelta(months=1)

            if period_to > date_to:
                period_to = date_to
            periods.append(
                (period_from, period_to)
            )
            period_from = period_to + relativedelta(days=1)
        return periods

    def minimize_execute(self, query, params):
        self._cr.execute(query, params)
        while 1:
            # http://initd.org/psycopg/docs/cursor.html#cursor.fetchmany
            # Set cursor.arraysize to minimize network round trips
            self._cr.arraysize = 1000
            rows = self._cr.fetchmany()
            if not rows:
                break
            for row in rows:
                yield row

    @api.multi
    def write_fec_lines(self, fec_file, delimiter, date_from, date_to,
                        extension):
        self.ensure_one()
        # if not os.path.exists(file_path):
        #     raise ValueError('File {} not found'.format(file_path))

        # fec_file = open(file_path, 'a+')
        w = csv.writer(fec_file, delimiter=delimiter)
        sql_query = '''
                SELECT
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
                    CASE WHEN rec.name IS NULL THEN '' ELSE rec.name END AS
                    EcritureLet,
                    CASE WHEN aml.full_reconcile_id IS NULL THEN '' ELSE
                    TO_CHAR(rec.create_date, 'YYYYMMDD') END AS DateLet,
                    TO_CHAR(am.date, 'YYYYMMDD') AS ValidDate,
                    CASE
                        WHEN aml.amount_currency IS NULL OR
                        aml.amount_currency = 0 THEN '' ELSE replace(
                        to_char(aml.amount_currency, '000000000000000D99'),
                        '.', ',')
                    END AS Montantdevise,
                    CASE WHEN aml.currency_id IS NULL THEN '' ELSE rc.name END
                    AS Idevise
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
                    aml.id
                '''
        company = self.env.user.company_id
        for row in self.minimize_execute(
                sql_query, (date_from, date_to, company.id)):
            listrow = list(row)
            w.writerow([s.encode("utf-8") for s in listrow])
        siren = company.vat[4:13]
        end_date = self.date_to.replace('-', '')
        suffix = ''
        timestamp = int(time.mktime(datetime.now().timetuple()))
        if self.export_type == "nonofficial":
            suffix = '-NONOFFICIAL'
        file_name = '{}FEC{}{}_{}.{}'.format(
            siren, end_date, suffix, timestamp, extension)
        return file_name, fec_file

    @api.model
    def cron_clean_fec_files(self):
        # Clean the past FEC files
        siren = self.env.user.company_id.vat[4:13]
        attachments = self.env['ir.attachment'].search([('name', 'like',
                                                         siren+'FEC')])
        for attachment in attachments:
            mail = self.env['mail.mail'].search([('attachment_ids', 'in',
                                                  [attachment.id])])
            if not mail:
                attachment.unlink()
            elif mail.state == 'sent':
                attachment.unlink()
        return True


@job
def write_fec_lines_session_job(
        session, model_name, session_list, date_from, date_to,
        delimiter='|', extension='csv'):
    """ Job to write FEC lines per period """
    fec_wizard = session.env[model_name].browse(session_list)
    fec_wizard.create_attachment(delimiter, date_from, date_to, extension)
