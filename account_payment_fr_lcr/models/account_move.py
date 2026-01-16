# Copyright 2024 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import io
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, format_date

logger = logging.getLogger(__name__)


try:
    from pypdf import PdfReader, PdfWriter
except (OSError, ImportError) as err:
    logger.debug(err)


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_method_line_fr_lcr_type = fields.Selection(
        related="preferred_payment_method_line_id.fr_lcr_type", store=True
    )
    fr_lcr_attachment_id = fields.Many2one(
        "ir.attachment", string="Bill of Exchange Attachment"
    )
    fr_lcr_attachment_name = fields.Char(
        related="fr_lcr_attachment_id.name", string="Bill of Exchange Filename"
    )
    fr_lcr_attachment_datas = fields.Binary(
        related="fr_lcr_attachment_id.datas", string="Bill of Exchange File"
    )
    fr_lcr_partner_bank_id = fields.Many2one(
        "res.partner.bank",
        compute="_compute_fr_lcr_partner_bank_id",
        store=True,
        readonly=False,
        string="Bill of Exchange Bank Account",
        help="Bank account of the customer that will be debited by "
        "the bill of exchange. By default, Odoo selects the first French "
        "IBAN bank account of the partner.",
        check_company=True,
        tracking=True,
        domain="[('partner_id', '=', commercial_partner_id)]",
    )

    @api.depends("partner_id", "preferred_payment_method_line_id")
    def _compute_fr_lcr_partner_bank_id(self):
        for move in self:
            partner_bank_id = False
            if (
                move.move_type == "out_invoice"
                and move.payment_method_code == "fr_lcr"
                and move.partner_id
                and move.partner_id.commercial_partner_id.bank_ids
            ):
                for partner_bank in move.partner_id.commercial_partner_id.bank_ids:
                    if (
                        partner_bank.acc_type == "iban"
                        and partner_bank.sanitized_acc_number
                        and partner_bank.sanitized_acc_number.startswith("FR")
                        and (
                            not partner_bank.company_id
                            or partner_bank.company_id == move.company_id
                        )
                    ):
                        partner_bank_id = partner_bank.id
                        break
            move.fr_lcr_partner_bank_id = partner_bank_id

    def _post(self, soft=True):
        for move in self:
            if move.move_type == "out_invoice" and move.payment_method_code == "fr_lcr":
                # We consider bank account as required only for letter of change,
                # not for promissory note (we may only know the bank account when
                # receiving it)
                if (
                    move.payment_method_line_fr_lcr_type in ("accepted", "not_accepted")
                    and not move.fr_lcr_partner_bank_id
                ):
                    raise UserError(
                        self.env._(
                            "Customer invoice '%(move)s' is configured with "
                            "payment mode '%(payment_method_line)s' which require "
                            "a bill of exchange bank account.",
                            move=move.display_name,
                            payment_method_line=move.preferred_payment_method_line_id.display_name,
                        )
                    )
                if move.fr_lcr_partner_bank_id:
                    move.fr_lcr_partner_bank_id._fr_iban_validate()
        return super()._post(soft=soft)

    def fr_lcr_print(self):
        self.ensure_one()
        assert self.state == "posted"
        assert self.move_type == "out_invoice"
        assert self.payment_method_code == "fr_lcr"
        assert self.payment_method_line_fr_lcr_type == "accepted"
        if self.fr_lcr_attachment_id and self.payment_state not in (
            "in_payment",
            "paid",
        ):
            self.fr_lcr_attachment_id.unlink()
        if not self.fr_lcr_attachment_id:
            self.fr_lcr_generate_attachment()
        action = {
            "name": self.fr_lcr_attachment_id.name,
            "type": "ir.actions.act_url",
            "url": f"web/content/?model={self._name}&id={self.id}&"
            f"filename_field=fr_lcr_attachment_name&field=fr_lcr_attachment_datas&"
            f"download=true&filename={self.fr_lcr_attachment_id.name}",
            "target": "new",
            # target: "new" and NOT "self", otherwise you get the following bug:
            # after this action, all UserError won't show a pop-up to the user
            # but will only show a warning message in the logs until the web
            # page is reloaded
        }
        return action

    def _prepare_fr_lcr_report_values(self):
        self.ensure_one()
        lang = "fr_FR"
        rib = self.fr_lcr_partner_bank_id._fr_iban2rib()
        # I take the commercial_partner, because I don't want to have the name
        # of a specific contact as customer address
        partner = self.commercial_partner_id
        company_partner = self.company_id.partner_id
        amount_value = format_amount(
            self.env, self.amount_residual, self.currency_id, lang_code=lang
        )
        ref_tire = self._get_payment_order_communication_direct()
        ref_tire_ascii = self.env["account.payment.order"]._prepare_lcr_field(
            "Reférence tiré", ref_tire, 10, reference=True
        )
        res = {
            "amount_check": {
                "value": amount_value,
                "x": 123,
                "y": 147,
                "align": "right",
            },
            "amount": {
                "value": amount_value,
                "x": 548,
                "y": 147,
                "align": "right",
            },
            "invoice_date": {
                "value": format_date(self.env, self.invoice_date, lang_code=lang),
                "x": 145,
                "y": 147,
            },
            "invoice_date_due": {
                "value": format_date(self.env, self.invoice_date_due, lang_code=lang),
                "x": 223,
                "y": 147,
            },
            "ref_tire": {
                "value": ref_tire_ascii,
                "x": 293,
                "y": 147,
            },
            "partner_address": {
                "value": partner._display_address(),
                "x": 251,
                "y": 43,
                "width": 403 - 251,
                "height": 91 - 43,
            },
            "company_address": {
                "value": company_partner._display_address(),
                "x": 46,
                "y": 202,
                "width": 202 - 46,
                "height": 255 - 202,
            },
            "company_name": {
                "value": company_partner.name,
                "x": 304,
                "y": 204,
            },
            "company_city": {
                "value": company_partner.city,
                "x": 63,
                "y": 181,
            },
            "rib_bank": {
                "value": rib["bank"],
                "x": 56,
                "y": 94,
            },
            "rib_branch": {
                "value": rib["branch"],
                "x": 99,
                "y": 94,
            },
            "rib_account": {
                "value": rib["account"],
                "x": 144,
                "y": 94,
            },
            "rib_key": {
                "value": rib["key"],
                "x": 219,
                "y": 94,
            },
            "bank_name": {
                "value": self.fr_lcr_partner_bank_id.bank_id.name,
                "x": 410,
                "y": 90,
            },
            "partner_siren": {
                "value": hasattr(partner, "siren") and partner.siren or False,
                "x": 115,
                "y": 40,
            },
        }
        return res

    def fr_lcr_generate_attachment(self):
        packet = io.BytesIO()
        # create a new PDF that contains the additional text with Reportlab
        text_canvas = canvas.Canvas(packet, pagesize=A4)
        text_canvas.setFont("Helvetica", 10)

        # for address blocks
        styleSheet = getSampleStyleSheet()
        style = styleSheet["BodyText"]
        style.fontSize = 8
        style.leading = 9

        # Add text strings and blocks
        report_values = self._prepare_fr_lcr_report_values()
        for field_name, field_val in report_values.items():
            if field_val["value"]:
                if field_name.endswith("_address"):
                    # Address => use flowable because it is multiline
                    addr_para = Paragraph(
                        field_val["value"].replace("\n", "<br/>"), style
                    )
                    addr_para.wrap(field_val["width"], field_val["height"])
                    addr_para.drawOn(text_canvas, field_val["x"], field_val["y"])
                elif field_val.get("align") == "right":
                    text_canvas.drawRightString(
                        field_val["x"], field_val["y"], field_val["value"]
                    )
                else:
                    text_canvas.drawString(
                        field_val["x"], field_val["y"], field_val["value"]
                    )
        text_canvas.save()

        # move to the beginning of the StringIO buffer
        packet.seek(0)
        watermark_pdf_reader = PdfReader(packet)
        # read your existing PDF
        with tools.file_open(
            "account_payment_fr_lcr/reports/lettre_de_change.pdf", "rb"
        ) as empty_report_fd:
            final_report_writer = PdfWriter(empty_report_fd)
            # add the "watermark" (which is the new pdf) on the existing page
            final_report_writer.pages[0].merge_page(watermark_pdf_reader.pages[0])
            final_report_writer.pages[0].compress_content_streams()
            # finally, write "output" to a real file
            final_report_io = io.BytesIO()
            final_report_writer.write(final_report_io)
            final_report_bytes = final_report_io.getvalue()

        filename = f"lettre_de_change-{self.name.replace('/', '-')}.pdf"
        attach = self.env["ir.attachment"].create(
            {
                "name": filename,
                "res_id": self.id,
                "res_model": self._name,
                "raw": final_report_bytes,
            }
        )
        self.write({"fr_lcr_attachment_id": attach.id})
