from odoo import models, fields, api
from odoo.addons.queue_job.job import job
from odoo.tools import pycompat

from dateutil.relativedelta import relativedelta
import io


class AccountFrFec(models.TransientModel):
    _inherit = 'account.fr.fec'

    @api.multi
    def write(self, vals):
        if self.env.context.get('extension', '') == 'txt' and \
                vals.get('filename'):
            vals['filename'] = vals['filename'][:-3] + 'txt'
        return super().write(vals)

    @api.multi
    def export_fec_txt(self):
        self.ensure_one()
        return self.with_context(
            extension="txt", delimiter='\t').generate_fec()

    @api.multi
    def export_fec_csv_background(self):
        self.ensure_one()
        return self.generate_fec_file_in_background()

    @api.multi
    def export_fec_txt_background(self):
        self.ensure_one()
        return self.generate_fec_file_in_background('txt', '\t')

    @api.multi
    def create_attachment(self, date_from, date_to, extension, delimeter):
        self.ensure_one()
        self.date_from = date_from
        self.date_to = date_to
        self.with_context(
            extension=extension, delimiter=delimeter).generate_fec()
        attachment = self.env["ir.attachment"].create(
            {
                "name": self.filename,
                "datas_fname": self.filename,
                "datas": self.fec_data,
            }
        )
        email_template = self.env.ref(
            "l10n_fr_fec_background.send_fec_file_mail_template"
        )
        mail_id = email_template.send_mail(self.id)
        mail = self.env['mail.mail'].browse(mail_id)
        mail.write({'attachment_ids': [(4, attachment.id)]})
        mail.send()
        return True

    @api.multi
    def generate_fec_file_in_background(self, extension="csv", delimiter="|"):
        self.ensure_one()
        # Prepare periods
        date_from = fields.Date.from_string(self.date_from)
        date_to = fields.Date.from_string(self.date_to)
        periods = self.prepare_periods(date_from, date_to)

        # Call job
        for (period_from, period_to) in periods:
            # Create jobs
            self.with_delay().write_fec_lines_session_job(
                period_from,
                period_to,
                extension,
                delimiter
            )
        return True

    @api.multi
    def prepare_periods(self, date_from, date_to):
        periods = []
        period_from = period_to = date_from
        while period_to < date_to:
            period_to = period_from + relativedelta(months=1)
            if period_to > date_to:
                period_to = date_to
            periods.append((period_from, period_to))
            period_from = period_to + relativedelta(days=1)
        return periods

    def _csv_write_rows(self, rows, lineterminator=u'\r\n'):
        """
        Write FEC rows into a file
        It seems that Bercy's bureaucracy is not too happy about the
        empty new line at the End Of File.

        @param {list(list)} rows: the list of rows. Each row is a list of
                                                                    strings
        @param {unicode string} [optional] lineterminator: effective line
                                                                    terminator
            Has nothing to do with the csv writer parameter
            The last line written won't be terminated with it

        @return the value of the file
        """
        fecfile = io.BytesIO()
        writer = pycompat.csv_writer(
            fecfile,
            delimiter=self.env.context.get('delimiter', '|'),
            lineterminator=''
        )

        rows_length = len(rows)
        for i, row in enumerate(rows):
            if not i == rows_length - 1:
                row[-1] = (row[-1] and row[-1] or '') + lineterminator
            writer.writerow(row)

        fecvalue = fecfile.getvalue()
        fecfile.close()
        return fecvalue

    @job
    def write_fec_lines_session_job(
            self, date_from, date_to, extension, delimiter):
        """ Job to write FEC lines per period """
        self.create_attachment(date_from, date_to, extension, delimiter)
