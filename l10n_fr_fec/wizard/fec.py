# -*- coding: utf-8 -*-
# © 2013-2017 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields, api, _
from openerp.exceptions import Warning as UserError
import base64
import StringIO
import logging
logger = logging.getLogger(__name__)

try:
    from unidecode import unidecode
except ImportError:
    logger.debug('Cannot import unidecode')
try:
    import unicodecsv
except ImportError:
    logger.debug('Cannot import unicodecsv')


class AccountFrFec(models.TransientModel):
    _name = 'account.fr.fec'
    _description = 'Ficher Echange Informatise'

    fiscalyear_id = fields.Many2one(
        'account.fiscalyear', string='Fiscal Year', required=True)
    type = fields.Selection([
        ('is_ir_bic', 'I.S. or BIC @ I.R.'),
        ], string='Company Type', default='is_ir_bic')
    encoding = fields.Selection([
        ('iso8859_15', 'ISO-8859-15'),
        ('utf-8', 'UTF-8'),
        ('ascii', 'ASCII'),
        ], string='Encoding', default='iso8859_15', required=True)
    fec_data = fields.Binary('FEC File', readonly=True)
    filename = fields.Char(string='Filename', size=256, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ], string='State', default='draft')
    export_type = fields.Selection([
        ('official', 'Official FEC report (posted entries only)'),
        (
            'nonofficial',
            'Non-official FEC report (posted and unposted entries)'),
        ], string='Export Type', required=True, default='official')

    @api.multi
    def generate_fec(self):
        self.ensure_one()
        assert self.fiscalyear_id.period_ids,\
            'The Fiscal Year must have periods'
        # We choose to implement the flat file instead of the XML
        # file for 2 reasons :
        # 1) the XSD file impose to have the label on the account.move
        # but Odoo has the label on the account.move.line, so that's a
        # problem !
        # 2) CSV files are easier to read/use for a regular accountant.
        # So it will be easier for the accountant to check the file before
        # sending it to the fiscal administration
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

        company = self.fiscalyear_id.company_id
        encoding = self.encoding

        sql_query = r'''
        SELECT
            regexp_replace(
            aj.code, E'[\n\r\t\|]+', '/', 'g') AS JournalCode,
            regexp_replace(
            aj.name, E'[\n\r\t\|]+', '/', 'g') AS JournalLib,
            regexp_replace(
            am.name, E'[\n\r\t\|]+', '/', 'g') AS EcritureNum,
            am.date AS EcritureDate,
            aa.code AS CompteNum,
            regexp_replace(
            aa.name, E'[\n\r\t\|]+', '/', 'g') AS CompteLib,
            CASE WHEN rp.ref IS null OR rp.ref = ''
            THEN 'ID ' || rp.id
            ELSE rp.ref
            END
            AS CompAuxNum,
            regexp_replace(
            rp.name, E'[\n\r\t\|]+', '/', 'g') AS CompAuxLib,
            CASE WHEN am.ref IS null OR am.ref = ''
            THEN '-'
            ELSE regexp_replace(
            am.ref, E'[\n\r\t\|]+', '/', 'g')
            END
            AS PieceRef,
            am.date AS PieceDate,
            regexp_replace(
            aml.name, E'[\n\r\t\|]+', '/', 'g') AS EcritureLib,
            aml.debit AS Debit,
            aml.credit AS Credit,
            regexp_replace(
            amr.name, E'[\n\r\t\|]+', '/', 'g') AS EcritureLet,
            amr.create_date::timestamp::date AS DateLet,
            am.date AS ValidDate,
            aml.amount_currency AS Montantdevise,
            rc.name AS Idevise
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id=aml.move_id
            LEFT JOIN res_partner rp ON rp.id=aml.partner_id
            LEFT JOIN account_move_reconcile amr ON amr.id = aml.reconcile_id
            JOIN account_journal aj ON aj.id = am.journal_id
            JOIN account_account aa ON aa.id = aml.account_id
            LEFT JOIN res_currency rc ON rc.id = aml.currency_id
        WHERE
            am.period_id IN %s
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
            CASE aj.type WHEN 'situation' THEN 1 ELSE 2 END,
            aml.id
        '''
        self._cr.execute(
            sql_query, (tuple(self.fiscalyear_id.period_ids.ids), company.id))

        fecfile = StringIO.StringIO()
        w = unicodecsv.writer(
            fecfile, encoding=encoding, errors='replace', delimiter='|')
        w.writerow(header)

        while 1:
            self._cr.arraysize = 100
            rows = self._cr.fetchmany()
            if not rows:
                break
            for row in rows:
                # We can't write in a tuple, so I convert to a list
                listrow = list(row)
                # Empty amount_currency i.e. remplace 0.0 by empty field
                if not listrow[16]:
                    listrow[16] = ''
                # Could we set the date format in the SQL query to avoid this?
                listrow[3] = listrow[3].replace('-', '')
                listrow[9] = listrow[9].replace('-', '')
                if listrow[14]:
                    listrow[14] = listrow[14].replace('-', '')
                listrow[15] = listrow[15].replace('-', '')
                # Decimal separator must be a coma
                listrow[11] = ('%.2f' % listrow[11]).replace('.', ',')
                listrow[12] = ('%.2f' % listrow[12]).replace('.', ',')
                if listrow[16]:
                    listrow[16] = ('%.2f' % listrow[16]).replace('.', ',')
                if encoding == 'ascii':
                    for char_col in [1, 5, 7, 8, 10]:
                        listrow[char_col] = unidecode(listrow[char_col])
                # I don't do a special treatment for 'latin1' ; I just
                # take advantage of unicodecsv.writer(errors='replace')
                # -> unicode caracters not available in latin1 will be
                # replaced by '?'
                w.writerow(listrow)

        if company.vat:
            vat = company.vat.replace(' ', '')
            if vat[0:2] != 'FR':
                raise UserError(_("FEC is for French companies only !"))
            siren = vat[4:13]
        elif company.siret:
            siren = company.siret[0:9]
        else:
            raise UserError(_(
                "Missing VAT number and SIRET for company %s") % company.name)
        fy_end_date = self.fiscalyear_id.date_stop.replace('-', '')
        suffix = ''
        if self.export_type == "nonofficial":
            suffix = '-NONOFFICIAL'
        fecvalue = fecfile.getvalue()
        self.write({
            'state': 'done',
            'fec_data': base64.encodestring(fecvalue),
            'filename': '%sFEC%s%s.csv' % (siren, fy_end_date, suffix),
            # Filename = <siren>FECYYYYMMDD where YYYMMDD is the closing date
            })
        fecfile.close()

        action = {
            'name': 'FEC',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'target': 'new',
            }
        return action
