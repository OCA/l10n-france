# Copyright 2017-2021 Akretion France (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import logging
import os.path
import tarfile
import time
from io import BytesIO

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang

logger = logging.getLogger(__name__)

CREDIT_TRF_CODES = ("30", "31", "42")
CHORUS_FILENAME_MAX = 50
CHORUS_FILESIZE_MAX_MO = 10
CHORUS_TOTAL_FILESIZE_MAX_MO = 120
CHORUS_TOTAL_ATTACHMENTS_MAX_MO = 118
CHORUS_ALLOWED_FORMATS = [
    ".BMP",
    ".GIF",
    ".FAX",
    ".ODT",
    ".PPT",
    ".TIFF",
    ".XLS",
    ".BZ2",
    ".GZ",
    ".JPEG",
    ".P7S",
    ".RTF",
    ".TXT",
    ".XML",
    ".CSV",
    ".GZIP",
    ".JPG",
    ".PDF",
    ".SVG",
    ".XHTML",
    ".XLSX",
    ".DOC",
    ".HTM",
    ".ODP",
    ".PNG",
    ".TGZ",
    ".XLC",
    ".ZIP",
    ".DOCX",
    ".HTML",
    ".ODS",
    ".PPS",
    ".TIF",
    ".XLM",
    ".PPTX",
]


class AccountMove(models.Model):
    _inherit = "account.move"

    chorus_flow_id = fields.Many2one(
        "chorus.flow", string="Chorus Flow", readonly=True, copy=False, tracking=True
    )
    chorus_identifier = fields.Integer(
        string="Chorus Invoice Identifier", readonly=True, copy=False, tracking=True
    )
    chorus_status = fields.Char(
        string="Chorus Invoice Status", readonly=True, copy=False, tracking=True
    )
    chorus_status_date = fields.Datetime(
        string="Last Chorus Invoice Status Update", readonly=True, copy=False
    )
    chorus_attachment_ids = fields.Many2many(
        "ir.attachment",
        "account_move_chorus_ir_attachment_rel",
        string="Chorus Attachments",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    @api.constrains("chorus_attachment_ids", "transmit_method_id")
    def _check_chorus_attachments(self):
        # https://communaute.chorus-pro.gouv.fr/pieces-jointes-dans-chorus-pro-quelques-regles-a-respecter/  # noqa: B950
        for move in self:
            if (
                move.move_type in ("out_invoice", "out_refund")
                and move.transmit_method_code == "fr-chorus"
            ):
                total_size = 0
                for attach in move.chorus_attachment_ids:
                    if len(attach.name) > CHORUS_FILENAME_MAX:
                        raise ValidationError(
                            _(
                                "On Chorus Pro, the attachment filename is %(filename_max)s "
                                "caracters maximum (extension included). The "
                                "filename '%(filename)s' has %(filename_size)s caracters."
                            )
                            % {
                                "filename_max": CHORUS_FILENAME_MAX,
                                "filename": attach.name,
                                "filename_size": len(attach.name),
                            }
                        )
                    filename, file_extension = os.path.splitext(attach.name)
                    if not file_extension:
                        raise ValidationError(
                            _(
                                "On Chorus Pro, the attachment filenames must "
                                "have an extension. The filename '%s' doesn't "
                                "have any extension."
                            )
                            % attach.name
                        )
                    if file_extension.upper() not in CHORUS_ALLOWED_FORMATS:
                        raise ValidationError(
                            _(
                                "On Chorus Pro, the allowed formats for the "
                                "attachments are the following: %(extension_list)s.\n"
                                "The attachment '%(filename)s' is not part of this list."
                            )
                            % {
                                "extension_list": ", ".join(CHORUS_ALLOWED_FORMATS),
                                "filename": attach.name,
                            }
                        )
                    if not attach.file_size:
                        raise ValidationError(
                            _("The size of the attachment '%s' is 0.")
                        )
                    total_size += attach.file_size
                    filesize_mo = round(attach.file_size / (1024 * 1024), 1)
                    if filesize_mo >= CHORUS_FILESIZE_MAX_MO:
                        raise ValidationError(
                            _(
                                "On Chorus Pro, each attachment cannot exceed %(size_max)s Mb. "
                                "The attachment '%(filename)s' weights %(size)s Mb."
                            )
                            % {
                                "size_max": CHORUS_FILESIZE_MAX_MO,
                                "filename": attach.name,
                                "size": formatLang(self.env, filesize_mo),
                            }
                        )
                if total_size:
                    total_size_mo = round(total_size / (1024 * 1024), 1)
                    if total_size_mo > CHORUS_TOTAL_ATTACHMENTS_MAX_MO:
                        raise ValidationError(
                            _(
                                "On Chorus Pro, an invoice with its attachments "
                                "cannot exceed %(size_max)s Mb, so we set a limit of "
                                "%(attach_size_max)s Mb for the attachments. "
                                "The attachments have a total size of %(size)s Mb."
                            )
                            % {
                                "size_max": CHORUS_TOTAL_FILESIZE_MAX_MO,
                                "attach_size_max": CHORUS_TOTAL_ATTACHMENTS_MAX_MO,
                                "size": formatLang(self.env, total_size_mo),
                            }
                        )

    def action_post(self):
        """Check validity of Chorus invoices"""
        for inv in self.filtered(
            lambda x: x.move_type in ("out_invoice", "out_refund")
            and x.transmit_method_code == "fr-chorus"
        ):
            inv._chorus_validation_checks()
        return super().action_post()

    def _chorus_validation_checks(self):
        self.ensure_one()
        self.company_id._chorus_common_validation_checks(
            self, self.partner_id, self.ref
        )
        if self.move_type == "out_invoice":
            if not self.payment_mode_id:
                raise UserError(
                    _(
                        "Missing Payment Mode on invoice '%s'. "
                        "This information is required for Chorus Pro."
                    )
                    % self.display_name
                )
            payment_means_code = (
                self.payment_mode_id.payment_method_id.unece_code or "30"
            )
            if payment_means_code in CREDIT_TRF_CODES:
                partner_bank_id = self.partner_bank_id or (
                    self.payment_mode_id.bank_account_link == "fixed"
                    and self.payment_mode_id.fixed_journal_id.bank_account_id
                )
                if not partner_bank_id:
                    raise UserError(
                        _(
                            "On invoice '%(invoice)s', the bank account information "
                            "of the issuer (%(company)s) is missing. "
                            "For that, you have two options: either the "
                            "payment mode of the invoice should have "
                            "'Link to Bank Account' = "
                            "'fixed' and the related bank journal should have "
                            "a 'Bank Account' set, or the field "
                            "'Bank Account' should be set on the customer "
                            "invoice."
                        )
                        % {
                            "invoice": self.display_name,
                            "company": self.company_id.display_name,
                        }
                    )
                if partner_bank_id.acc_type != "iban":
                    raise UserError(
                        _(
                            "Chorus Pro only accepts IBAN. But the bank account "
                            "'%(acc_number)s' of %(company)s is not an IBAN."
                        )
                        % {
                            "acc_number": partner_bank_id.acc_number,
                            "company": self.company_id.display_name,
                        }
                    )
        elif self.move_type == "out_refund":
            if self.payment_mode_id:
                raise UserError(
                    _(
                        "The Payment Mode must be empty on %s "
                        "because customer refunds sent to Chorus Pro mustn't "
                        "have a Payment Mode."
                    )
                    % self.display_name
                )

    def chorus_get_invoice(self, chorus_invoice_format):
        self.ensure_one()
        return False

    def prepare_chorus_deposer_flux_payload(self):
        if not self[0].company_id.fr_chorus_invoice_format:
            raise UserError(
                _(
                    "The Chorus Invoice Format is not configured on the "
                    "Accounting Configuration page of company '%s'."
                )
                % self[0].company_id.display_name
            )
        chorus_invoice_format = self[0].company_id.fr_chorus_invoice_format
        short_format = chorus_invoice_format[4:]
        file_extension = chorus_invoice_format[:3]
        syntaxe_flux = self.env["chorus.flow"].syntax_odoo2chorus()[
            chorus_invoice_format
        ]
        if len(self) == 1:
            chorus_file_content = self.chorus_get_invoice(chorus_invoice_format)
            filename = "%s_chorus_facture_%s.%s" % (
                short_format,
                self.name.replace("/", "-"),
                file_extension,
            )
        else:
            filename = "%s_chorus_lot_factures.tar.gz" % short_format
            tarfileobj = BytesIO()
            with tarfile.open(fileobj=tarfileobj, mode="w:gz") as tar:
                for inv in self:
                    inv_file_data = inv.chorus_get_invoice(chorus_invoice_format)
                    invfileio = BytesIO(inv_file_data)
                    invfilename = "%s_chorus_facture_%s.%s" % (
                        short_format,
                        inv.name.replace("/", "-"),
                        file_extension,
                    )
                    tarinfo = tarfile.TarInfo(name=invfilename)
                    tarinfo.size = len(inv_file_data)
                    tarinfo.mtime = int(time.time())
                    tar.addfile(tarinfo=tarinfo, fileobj=invfileio)
                tar.close()
            tarfileobj.seek(0)
            chorus_file_content = tarfileobj.read()
        payload = {
            "fichierFlux": base64.b64encode(chorus_file_content).decode("ascii"),
            "nomFichier": filename,
            "syntaxeFlux": syntaxe_flux,
            "avecSignature": False,
        }
        return payload

    def chorus_api_consulter_historique(self, api_params, session=None):
        url_path = "factures/v1/consulter/historique"
        payload = {
            "idFacture": self.chorus_identifier,
        }
        answer, session = self.env["res.company"].chorus_post(
            api_params, url_path, payload, session=session
        )
        res = False
        if (
            answer.get("idFacture")
            and answer["idFacture"] == self.chorus_identifier
            and answer.get("statutCourantCode")
        ):
            res = answer["statutCourantCode"]
        return (res, session)

    def chorus_update_invoice_status(self):
        """Called by a button on the invoice or by cron"""
        logger.info("Start to update chorus invoice status")
        company2api = {}
        raise_if_ko = self._context.get("chorus_raise_if_ko", True)
        invoices = []
        for inv in self:
            if not inv.chorus_identifier:
                if raise_if_ko:
                    raise UserError(
                        _("Missing Chorus Invoice Identifier on invoice '%s'.")
                        % inv.display_name
                    )
                logger.warning(
                    "Skipping invoice %s: missing chorus invoice identifier", inv.name
                )
                continue
            company = inv.company_id
            if company not in company2api:
                api_params = company.chorus_get_api_params(raise_if_ko=raise_if_ko)
                if not api_params:
                    continue
                company2api[company] = api_params
            invoices.append(inv)
        session = None
        for invoice in invoices:
            api_params = company2api[invoice.company_id]
            inv_status, session = invoice.chorus_api_consulter_historique(
                api_params, session
            )
            if inv_status:
                invoice.write(
                    {
                        "chorus_status": inv_status,
                        "chorus_status_date": fields.Datetime.now(),
                    }
                )
        logger.info("End of the update of chorus invoice status")
