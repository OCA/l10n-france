from dateutil.relativedelta import relativedelta

from odoo import Command, fields, models

from odoo.addons.queue_job.job import identity_exact


class AccountFrFecOca(models.TransientModel):
    _inherit = "account.fr.fec.oca"

    def write(self, vals):
        if self._context.get("extension", "") == "txt" and vals.get("filename"):
            vals["filename"] = vals["filename"][:-3] + "txt"
        return super().write(vals)

    def generate_fec(self):
        action = super().generate_fec()
        action.update(
            {
                "url": f"web/content/?model={self._name}&id={self.id}&filename_field="
                f"filename&field=fec_data&download=true&filename={self.filename}",
            }
        )
        return action

    def generate_fec_txt(self):
        self.ensure_one()
        return self.with_context(extension="txt").generate_fec()

    def generate_fec_background(self):
        self.ensure_one()
        return self.generate_fec_file_in_background()

    def generate_fec_txt_background(self):
        self.ensure_one()
        return self.generate_fec_file_in_background("txt")

    def send_fec(self, date_from, date_to, extension):
        self.ensure_one()
        self.date_from = date_from
        self.date_to = date_to
        _ = self.with_context(extension=extension).generate_fec()
        attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", self._name),
                ("res_field", "=", "fec_data"),
                ("res_id", "in", self.ids),
            ],
            limit=1,
            order="create_date desc",
        )
        attachments.write(
            {
                "name": self.filename,
                "mimetype": "text/plain",
            }
        )
        email_template = self.env.ref(
            "l10n_fr_fec_background.send_fec_file_mail_template"
        )
        email_template.send_mail(
            self.id,
            force_send=True,
            email_values={"attachment_ids": [Command.set(attachments.ids)]},
        )
        return True

    def generate_fec_file_in_background(self, extension="csv"):
        self.ensure_one()
        # Prepare periods
        date_from = fields.Date.from_string(self.date_from)
        date_to = fields.Date.from_string(self.date_to)
        periods = self.prepare_periods(date_from, date_to)

        # Call job
        for period_from, period_to in periods:
            self.write_fec_lines_session_job(period_from, period_to, extension)
        return True

    def prepare_periods(self, date_from, date_to):
        periods = []
        current_start = date_from

        while current_start <= date_to:
            current_end = current_start + relativedelta(day=31)
            if current_end > date_to:
                current_end = date_to

            periods.append((current_start, current_end))
            current_start = current_end + relativedelta(days=1)

        return periods

    def write_fec_lines_session_job(self, date_from, date_to, extension):
        """Job to write FEC lines per period"""
        self.with_delay(
            identity_key=identity_exact,
            description="Create FEC attachment",
        ).send_fec(date_from, date_to, extension)
