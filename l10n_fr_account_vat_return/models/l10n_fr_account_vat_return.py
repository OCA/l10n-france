# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import io
import json
import logging
import textwrap
import zipfile
from collections import defaultdict

import xlsxwriter
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from odoo import Command, _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils, float_compare, float_is_zero, float_round
from odoo.tools.misc import format_amount, format_date, formatLang

from .l10n_fr_account_vat_box import PUSH_RATE_PRECISION

logger = logging.getLogger(__name__)

try:
    from pypdf import PdfReader, PdfWriter
except (OSError, ImportError) as err:
    logger.debug(err)

MINIMUM_AMOUNT = 760
MINIMUM_END_YEAR_AMOUNT = 150

MONTH2QUARTER = {
    1: 1,
    4: 2,
    7: 3,
    10: 4,
}


class L10nFrAccountVatReturn(models.Model):
    _name = "l10n.fr.account.vat.return"
    _description = "France VAT Return (CA3)"
    _order = "start_date desc"
    _check_company_auto = True
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(compute="_compute_name_end_date", string="Period", store=True)
    # The default value of the start_date is set by the onchange on company_id
    start_date = fields.Date(
        required=True,
        readonly=True,
        states={"manual": [("readonly", False)]},
        tracking=True,
        compute="_compute_start_date",
        store=True,
        precompute=True,
    )
    vat_periodicity = fields.Selection(
        [
            ("1", "Monthly"),
            ("3", "Quarterly"),
            ("12", "Yearly"),
        ],
        string="VAT Periodicity",
        required=True,
        tracking=True,
        readonly=True,
        states={"manual": [("readonly", False)]},
        compute="_compute_start_date",
        store=True,
        precompute=True,
    )
    end_date = fields.Date(compute="_compute_name_end_date", store=True)
    vat_on_payment_option = fields.Selection(
        [
            ("native", "Native Odoo"),
            ("non_native", "Non-native (recommended)"),
        ],
        compute="_compute_vat_on_payment_option",
        store=True,
        string="VAT on Payment Option",
    )
    company_id = fields.Many2one(
        "res.company",
        ondelete="cascade",
        required=True,
        readonly=True,
        states={"manual": [("readonly", False)]},
        default=lambda self: self.env.company,
        tracking=True,
    )
    company_partner_id = fields.Many2one(
        related="company_id.partner_id", string="Company Partner"
    )
    bank_account_id = fields.Many2one(
        "res.partner.bank",
        string="Company Bank Account",
        states={"sent": [("readonly", True)], "posted": [("readonly", True)]},
        check_company=True,
        domain="[('partner_id','=', company_partner_id), "
        "'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        ondelete="restrict",
        compute="_compute_bank_account_id",
        store=True,
        readonly=False,
        precompute=True,
    )
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", store=True, string="Company Currency"
    )
    state = fields.Selection(
        [
            ("manual", "Manual Lines"),
            ("auto", "Automatic Lines"),
            ("sent", "Sent"),
            ("posted", "Posted"),
        ],
        default="manual",
        required=True,
        readonly=True,
        tracking=True,
    )
    move_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        readonly=True,
        tracking=True,
        check_company=True,
    )
    vat_credit_total = fields.Integer(string="VAT Credit Total", readonly=True)
    # When reimbursement_type = False, the other reimbursement fields are hidden
    reimbursement_min_amount = fields.Integer(
        compute="_compute_name_end_date", store=True
    )
    reimbursement_type = fields.Selection(
        "_reimbursement_type_selection", readonly=True
    )
    reimbursement_first_creation_date = fields.Date(
        string="Creation Date", readonly=True
    )
    reimbursement_end_date = fields.Date(string="Event Date", readonly=True)
    reimbursement_show_button = fields.Boolean(
        compute="_compute_reimbursement_show_button",
        string="Show VAT Credit Reimbursement Button",
    )
    reimbursement_comment_dgfip = fields.Text(
        string="Reimbursement Comment for DGFiP",
        states={"sent": [("readonly", True)], "posted": [("readonly", True)]},
    )
    ca3_attachment_id = fields.Many2one("ir.attachment", string="CA3 Attachment")
    ca3_attachment_datas = fields.Binary(
        related="ca3_attachment_id.datas", string="CA3 File"
    )
    ca3_attachment_name = fields.Char(
        related="ca3_attachment_id.name", string="CA3 Filename"
    )
    comment_dgfip = fields.Text(
        string="Comment for DGFiP",
        states={"sent": [("readonly", True)], "posted": [("readonly", True)]},
    )
    line_ids = fields.One2many(
        "l10n.fr.account.vat.return.line",
        "parent_id",
        string="Return Lines",
        readonly=True,
        states={"manual": [("readonly", False)]},
    )
    autoliq_line_ids = fields.One2many(
        "l10n.fr.account.vat.return.autoliq.line",
        "parent_id",
        string="Autoliquidation Lines",
        readonly=True,
    )
    unpaid_vat_on_payment_manual_line_ids = fields.One2many(
        "l10n.fr.account.vat.return.unpaid.vat.on.payment.manual.line",
        "parent_id",
        readonly=True,
        states={"manual": [("readonly", False)]},
    )
    ignore_draft_moves = fields.Boolean()  # technical field, not displayed
    autoliq_manual_done = fields.Boolean()  # technical field, not displayed
    # technical field used as filter for
    # l10n.fr.account.vat.return.unpaid.vat.on.payment.manual.line, not displayed
    unpaid_vat_on_payment_manual_line_filter_account_ids = fields.Many2many(
        "account.account",
        compute="_compute_unpaid_vat_on_payment_manual_line_filter_account_ids",
        store=True,
        precompute=True,
    )
    deductible_vat_zip_other_threshold = fields.Monetary(
        string="Threshold to provide non-asset invoices in ZIP",
        currency_field="company_currency_id",
        default=500,
        tracking=True,
        help="When generating the deductible VAT justification ZIP file, do not provide "
        "a copy of the non-asset invoice whose total untaxed amount in company "
        "currency is under that threshold.",
    )
    deductible_vat_zip_file_id = fields.Many2one(
        "ir.attachment", string="Deductible VAT ZIP Attachment"
    )
    deductible_vat_zip_file_datas = fields.Binary(
        related="deductible_vat_zip_file_id.datas", string="Deductible VAT ZIP File"
    )
    deductible_vat_zip_file_name = fields.Char(
        related="deductible_vat_zip_file_id.name", string="Deductible VAT ZIP Filename"
    )
    sent_datetime = fields.Datetime(string="Sent Date", readonly=True)
    send_gateway = fields.Selection(
        "_send_gateway_selection",
        compute="_compute_send_gateway",
        store=True,
        readonly=False,
        precompute=True,
    )
    gateway_available = fields.Boolean(compute="_compute_gateway_available")
    gateway_test_mode = fields.Boolean(compute="_compute_gateway_test_mode")
    gateway_attachment_id = fields.Many2one(
        "ir.attachment", readonly=True, string="Data Sent via the Gateway"
    )

    _sql_constraints = [
        (
            "start_company_uniq",
            "unique(start_date, company_id)",
            "A VAT return with the same start date already exists in this company!",
        ),
        (
            "deductible_vat_zip_other_threshold_positive",
            "CHECK(deductible_vat_zip_other_threshold >= 0)",
            "The threshold to provide non-asset invoices in ZIP must be positive.",
        ),
    ]

    @api.model
    def _reimbursement_type_selection(self):
        return [
            ("first", "Demande déposée suite à première demande"),
            (
                "end",
                "Demande déposée suite à cession ou cessation ou décès ou "
                "entrée dans un groupe TVA",
            ),
            ("other", "Demande déposée suite à autres motifs"),
        ]

    @api.model
    def _send_gateway_selection(self):
        return []

    @api.constrains("start_date", "vat_periodicity")
    def _check_start_date(self):
        for rec in self:
            if rec.start_date.day != 1:
                raise ValidationError(
                    _(
                        "The start date (%s) must be the first day of the month.",
                        format_date(self.env, rec.start_date),
                    )
                )
            if rec.vat_periodicity == "3" and rec.start_date.month not in MONTH2QUARTER:
                raise ValidationError(
                    _(
                        "The start date (%s) must be the first day of a quarter.",
                        format_date(self.env, rec.start_date),
                    )
                )

    @api.constrains("comment_dgfip", "reimbursement_comment_dgfip")
    def _check_comment_dgfip(self):
        max_comment = 5 * 512
        comment_fields = {
            "comment_dgfip": _("Comment for DGFiP"),
            "reimbursement_comment_dgfip": _("Reimbursement Comment for DGFiP"),
        }
        for rec in self:
            for field_name, field_label in comment_fields.items():
                if rec[field_name] and len(rec[field_name]) > max_comment:
                    raise ValidationError(
                        _(
                            "The field '%(field_label)s' is too long: "
                            "it has %(count_char)d caracters "
                            "whereas the maximum is %(max_char)d caracters.",
                            field_label=field_label,
                            count_char=len(rec[field_name]),
                            max_char=max_comment,
                        )
                    )

    @api.depends("start_date", "vat_periodicity")
    def _compute_name_end_date(self):
        for rec in self:
            end_date = name = False
            reimbursement_min_amount = MINIMUM_AMOUNT
            if rec.start_date and rec.vat_periodicity:
                start_date = rec.start_date
                end_date = start_date + relativedelta(
                    months=int(rec.vat_periodicity), days=-1
                )
                if rec.vat_periodicity == "1":
                    name = start_date.strftime("%Y-%m")
                elif rec.vat_periodicity == "3":
                    quarter = MONTH2QUARTER.get(start_date.month, "error")
                    name = f"{start_date.year}-T{quarter}"
                elif rec.vat_periodicity == "12":
                    if start_date.month == 1:
                        name = str(start_date.year)
                    else:
                        name = f"{start_date.year}-{end_date.year}"
                if end_date.month == 12 or rec.vat_periodicity == "12":
                    reimbursement_min_amount = MINIMUM_END_YEAR_AMOUNT
            rec.name = name
            rec.end_date = end_date
            rec.reimbursement_min_amount = reimbursement_min_amount

    @api.depends("vat_periodicity")
    def _compute_gateway_available(self):
        gw_sel = self._send_gateway_selection()
        for rec in self:
            if rec.vat_periodicity in ("1", "3"):
                gateway_available = bool(gw_sel)
            else:
                gateway_available = False
            rec.gateway_available = gateway_available

    def _compute_gateway_test_mode(self):
        running_env = tools.config.get("running_env")
        test_mode = running_env in ("test", "dev")
        for rec in self:
            rec.gateway_test_mode = test_mode

    @api.depends("company_id")
    def _compute_send_gateway(self):
        gw_sel = self._send_gateway_selection()
        for rec in self:
            send_gateway = False
            if rec.company_id and rec.company_id.fr_vat_send_gateway:
                send_gateway = rec.company_id.fr_vat_send_gateway
            if not send_gateway and gw_sel:
                send_gateway = gw_sel[0][0]
            rec.send_gateway = send_gateway

    @api.depends(
        "reimbursement_min_amount", "vat_credit_total", "state", "reimbursement_type"
    )
    def _compute_reimbursement_show_button(self):
        for rec in self:
            reimbursement_show_button = False
            if (
                rec.state == "auto"
                and rec.vat_credit_total
                and rec.vat_credit_total >= rec.reimbursement_min_amount
                and not rec.reimbursement_type
            ):
                reimbursement_show_button = True
            rec.reimbursement_show_button = reimbursement_show_button

    @api.depends("company_id")
    def _compute_unpaid_vat_on_payment_manual_line_filter_account_ids(self):
        tax_base_domain = [
            ("amount_type", "=", "percent"),
            ("amount", ">", 0),
            ("unece_type_code", "=", "VAT"),
            ("country_id", "=", self.env.ref("base.fr").id),
            ("fr_vat_autoliquidation", "=", False),
        ]
        for rec in self:
            vat_account_ids = set()
            if rec.company_id:
                domain = tax_base_domain + [("company_id", "=", rec.company_id.id)]
                if rec.company_id.fr_vat_exigibility == "on_invoice":
                    domain += [("type_tax_use", "=", "purchase")]
                taxes = self.env["account.tax"].search(domain)
                rlines = self.env["account.tax.repartition.line"].search(
                    [
                        ("invoice_tax_id", "in", taxes.ids),
                        ("repartition_type", "=", "tax"),
                        ("factor_percent", ">", 99.9),
                        ("account_id", "!=", False),
                    ]
                )
                for rline in rlines:
                    vat_account_ids.add(rline.account_id.id)
            rec.unpaid_vat_on_payment_manual_line_filter_account_ids = list(
                vat_account_ids
            )

    @api.depends("company_id")
    def _compute_bank_account_id(self):
        for rec in self:
            rec.bank_account_id = rec.company_id.fr_vat_bank_account_id.id or False

    @api.depends("company_id")
    def _compute_start_date(self):
        today = fields.Date.context_today(self)
        for rec in self:
            vat_periodicity = rec.company_id.fr_vat_periodicity or False
            start_date = False
            if rec.company_id and vat_periodicity:
                last_return = self.search(
                    [("company_id", "=", rec.company_id.id)],
                    limit=1,
                    order="start_date desc",
                )
                if last_return:
                    start_date = last_return.end_date + relativedelta(days=1)
                else:
                    if vat_periodicity == "1":
                        start_date = today + relativedelta(months=-1, day=1)
                    elif vat_periodicity == "3":
                        start_date = today + relativedelta(months=-3, day=1)
                        while start_date.month not in MONTH2QUARTER:
                            start_date -= relativedelta(months=1)
                    elif vat_periodicity == "12":
                        start_date, fy_date_to = date_utils.get_fiscal_year(
                            today + relativedelta(years=-1),
                            day=rec.company_id.fiscalyear_last_day,
                            month=int(rec.company_id.fiscalyear_last_month),
                        )
            rec.start_date = start_date
            rec.vat_periodicity = vat_periodicity

    @api.depends("company_id")
    def _compute_vat_on_payment_option(self):
        for rec in self:
            option = "non_native"
            if rec.company_id.tax_exigibility:
                option = "native"
            rec.vat_on_payment_option = option

    @api.depends("name", "vat_periodicity")
    def name_get(self):
        res = []
        for rec in self:
            if rec.vat_periodicity == "12":
                name = f"CA12 {rec.name}"
            else:
                name = f"CA3 {rec.name}"
            res.append((rec.id, name))
        return res

    def auto2sent_via_gateway(self):
        self.ensure_one()
        assert self.state == "auto"
        if self.vat_periodicity not in ("1", "3"):
            raise UserError(
                _(
                    "The transmission of the VAT return %s via a gateway is not possible. "
                    "It is only possible for monthly and quarterly periodicity.",
                    self.display_name,
                )
            )
        if not self.send_gateway:
            raise UserError(
                _("No gateway selected for VAT return %s.", self.display_name)
            )
        if not self.line_ids:
            raise UserError(_("VAT return %s has no lines.", self.display_name))
        method_name = f"_send_via_{self.send_gateway}"
        if not hasattr(self, method_name):
            raise UserError(
                _("Method %s not available. This should never happen.", method_name)
            )
        method = getattr(self, method_name)
        # All failures should raise an Error in method()
        if self.gateway_test_mode:
            logger.info(
                "Gateway is in test mode: this VAT return will NOT be sent to DGFiP."
            )
        else:
            logger.info(
                "Gateway in production mode: this VAT return will be sent to DGFiP."
            )
        raw_bytes, extension = method(test_mode=self.gateway_test_mode)
        if raw_bytes and extension:
            now_dt = fields.Datetime.now()
            fnametime = now_dt.strftime("%Y-%m-%dT%H_%M_%S")
            filename = f"{self.send_gateway}-{fnametime}-UTC.{extension}"
            gw2label = dict(
                self.fields_get("send_gateway", "selection")["send_gateway"][
                    "selection"
                ]
            )
            attach = self.env["ir.attachment"].create(
                {
                    "name": filename,
                    "raw": raw_bytes,
                }
            )
            self.message_post(
                body=Markup(
                    _(
                        "VAT return successfully sent via %(gw)s%(test_mode_str)s. "
                        "Technical data sent: <a href=# data-oe-model=ir.attachment "
                        "data-oe-id=%(attach_id)s>%(attach_name)s</a>",
                        gw=gw2label[self.send_gateway],
                        test_mode_str=self.gateway_test_mode
                        and " " + _("in <strong>test mode</strong>")
                        or "",
                        attach_id=attach.id,
                        attach_name=attach.name,
                    )
                )
            )
            self._auto2sent(gateway_attachment_id=attach.id)

    def _prepare_speedy(self):
        # Generate a speed-dict called speedy that is used in several methods
        # or for some domains that we may need to inherit
        self.ensure_one()
        company_domain = [("company_id", "=", self.company_id.id)]
        base_domain = company_domain + [("parent_state", "=", "posted")]
        sale_journals = self.env["account.journal"].search(
            company_domain + [("type", "=", "sale")]
        )
        base_domain_period_sale = base_domain + [
            ("date", ">=", self.start_date),
            ("date", "<=", self.end_date),
            ("journal_id", "in", sale_journals.ids),
        ]
        base_domain_end = base_domain + [("date", "<=", self.end_date)]
        vat_tax_domain = company_domain + [
            ("amount_type", "=", "percent"),
            ("amount", ">", 0),
            ("unece_type_code", "=", "VAT"),
            ("country_id", "=", self.env.ref("base.fr").id),
        ]
        sale_regular_vat_tax_domain = vat_tax_domain + [
            ("fr_vat_autoliquidation", "=", False),
            ("type_tax_use", "=", "sale"),
        ]
        purchase_vat_tax_domain = vat_tax_domain + [("type_tax_use", "=", "purchase")]
        purchase_autoliq_vat_tax_domain = purchase_vat_tax_domain + [
            ("fr_vat_autoliquidation", "=", "total"),
        ]
        movetype2label = dict(
            self.env["account.move"].fields_get("move_type", "selection")["move_type"][
                "selection"
            ]
        )
        fp_frvattype2label = dict(
            self.env["account.fiscal.position"].fields_get("fr_vat_type", "selection")[
                "fr_vat_type"
            ]["selection"]
        )
        meaning_id2box = {}
        for box in self.env["l10n.fr.account.vat.box"].search(
            [("meaning_id", "!=", False)]
        ):
            meaning_id2box[box.meaning_id] = box
        speedy = {
            "company_id": self.company_id.id,
            "currency": self.company_id.currency_id,
            "native_vat_on_payment": self.vat_on_payment_option == "native",
            "company_domain": company_domain,
            "base_domain": base_domain,
            "base_domain_period_sale": base_domain_period_sale,
            "base_domain_end": base_domain_end,
            "sale_regular_vat_tax_domain": sale_regular_vat_tax_domain,
            "purchase_vat_tax_domain": purchase_vat_tax_domain,
            "purchase_autoliq_vat_tax_domain": purchase_autoliq_vat_tax_domain,
            "end_date_formatted": format_date(self.env, self.end_date),
            "start_date_formatted": format_date(self.env, self.start_date),
            "movetype2label": movetype2label,
            "fp_frvattype2label": fp_frvattype2label,
            "line_obj": self.env["l10n.fr.account.vat.return.line"],
            "log_obj": self.env["l10n.fr.account.vat.return.line.log"],
            "autoliq_line_obj": self.env["l10n.fr.account.vat.return.autoliq.line"],
            "box_obj": self.env["l10n.fr.account.vat.box"],
            "aa_obj": self.env["account.account"],
            "am_obj": self.env["account.move"],
            "aml_obj": self.env["account.move.line"],
            "aj_obj": self.env["account.journal"],
            "afp_obj": self.env["account.fiscal.position"],
            "afpt_obj": self.env["account.fiscal.position.tax"],
            "afpa_obj": self.env["account.fiscal.position.account"],
            "at_obj": self.env["account.tax"],
            "aadmo_obj": self.env["account.analytic.distribution.model"],
            "meaning_id2box": meaning_id2box,
            "box2value": {},  # used to speedy-up checks
            # used to create negative boxes at the end
            "negative_box2logs": defaultdict(list),
            "vat_groups": ["regular", "extracom_product", "oil"],
        }
        speedy["bank_cash_journals"] = speedy["aj_obj"].search(
            speedy["company_domain"] + [("type", "in", ("bank", "cash"))]
        )
        # I can't put this check in self._setup_data_pre_check()
        # because it has to be made BEFORE _autoliq_prepare_speedy()
        bad_fp = speedy["afp_obj"].search(
            speedy["company_domain"] + [("fr_vat_type", "=", False)], limit=1
        )
        if bad_fp:
            raise UserError(
                _(
                    "Type not set on fiscal position '%s'. It must be set on all "
                    "fiscal positions.",
                    bad_fp.display_name,
                )
            )
        self._france_due_vat_prepare_speedy(speedy)
        self._autoliq_prepare_speedy(speedy)
        return speedy

    def _autoliq_prepare_speedy(self, speedy):
        speedy.update(
            {
                "autoliq_taxedop_type2accounts": {
                    "intracom": speedy["aa_obj"],  # recordset 445201, 445202, 445203
                    "extracom": speedy["aa_obj"],  # recordset 445301, 445302, 445303
                    "france": speedy["aa_obj"],  # BTP subcontracting
                },
                "autoliq_vat_account2rate": {},
                # {445201: 2000, 445202: 1000, 445203: 55, 445301: 2000,  }
                "autoliq_tax2rate": {},
                # {TVA 20% intracom (achats): 2000, TVA 10% intracom (achats): 1000, }
            }
        )
        autoliq_vat_taxes = speedy["at_obj"].search(
            speedy["purchase_autoliq_vat_tax_domain"]
        )
        fr_vat_type2autoliq_type = {
            "intracom_b2b": "intracom",
            "extracom": "extracom",
            "france_exo": "france",
        }
        for tax in autoliq_vat_taxes:
            lines = tax.invoice_repartition_line_ids.filtered(
                lambda x: x.repartition_type == "tax"
                and x.account_id
                and int(x.factor_percent) == -100
            )
            if len(lines) != 1:
                raise UserError(
                    _(
                        "On the autoliquidation tax '%(tax)s', the distribution for "
                        "invoices should have only one line -100% of tax, and not "
                        "%(count)s.",
                        tax=tax.with_context(append_type_to_tax_name=True).display_name,
                        count=len(lines),
                    )
                )
            account = lines.account_id
            rate_int = int(tax.amount * 100)
            speedy["autoliq_tax2rate"][tax] = rate_int
            if (
                account in speedy["autoliq_vat_account2rate"]
                and speedy["autoliq_vat_account2rate"][account] != rate_int
            ):
                raise UserError(
                    _(
                        "Account '%(account)s' is used as due VAT account on several "
                        "autoliquidation taxes for different rates "
                        "(%(rate1).2f%% and %(rate2).2f%%).",
                        account=account.display_name,
                        rate1=rate_int / 100,
                        rate2=speedy["autoliq_vat_account2rate"][account] / 100,
                    )
                )
            if account in speedy["france_due_vat_account2rate"]:
                raise UserError(
                    _(
                        "Account '%(account)s' is used as due VAT account on "
                        "autoliquidation tax '%(tax)s' and also "
                        "on a regular sale tax with rate %(rate).2f%%.",
                        account=account.display_name,
                        tax=tax.with_context(append_type_to_tax_name=True).display_name,
                        rate=speedy["france_due_vat_account2rate"][account] / 100,
                    )
                )
            # Since May 2023, the new strategy to separate goods vs services
            # for intracom autoliq base is by analyzing unreconciled lines,
            # and not by analysing the VAT period only (which requires that the balance
            # of the account is 0 at the start of the period).
            # So the minimum is to make sure that the account has reconcile=True !
            if not account.reconcile:
                raise UserError(
                    _(
                        "Account '%s' is an account for autoliquidation, "
                        "so it's reconcile option must be enabled.",
                        account.display_name,
                    )
                )
            speedy["autoliq_vat_account2rate"][account] = rate_int
            tax_map = speedy["afpt_obj"].search(
                [
                    ("tax_dest_id", "=", tax.id),
                    ("company_id", "=", speedy["company_id"]),
                ],
                limit=1,
            )
            if not tax_map:
                raise UserError(
                    _(
                        "Autoliquidation tax '%s' is not present in the tax mapping "
                        "of any fiscal position.",
                        tax.with_context(append_type_to_tax_name=True).display_name,
                    )
                )
            fr_vat_type = tax_map.position_id.fr_vat_type
            if fr_vat_type not in fr_vat_type2autoliq_type:
                raise UserError(
                    _(
                        "The autoliquidation tax '%(tax)s' is set on the tax mapping "
                        "of fiscal position '%(fp)s' which is configured with type "
                        "'%(fp_fr_vat_type)s'. Autoliquidation taxes should only be configured "
                        "on fiscal positions with type '%(fp_fr_vat_type_intracom_b2b)s', "
                        "'%(fp_fr_vat_type_extracom)s' or '%(fp_fr_vat_type_france_exo)s'.",
                        tax=tax.with_context(append_type_to_tax_name=True).display_name,
                        fp=tax_map.position_id.display_name,
                        fp_fr_vat_type=speedy["fp_frvattype2label"][fr_vat_type],
                        fp_fr_vat_type_intracom_b2b=speedy["fp_frvattype2label"][
                            "intracom_b2b"
                        ],
                        fp_fr_vat_type_extracom=speedy["fp_frvattype2label"][
                            "extracom"
                        ],
                        fp_fr_vat_type_france_exo=speedy["fp_frvattype2label"][
                            "france_exo"
                        ],
                    )
                )
            autoliq_type = fr_vat_type2autoliq_type[fr_vat_type]
            speedy["autoliq_taxedop_type2accounts"][autoliq_type] |= account
        self._royalty_autoliq_prepare_speedy(speedy)

    def _royalty_autoliq_prepare_speedy(self, speedy):
        # Search the single royalty purchase VAT tax
        candidate_royalty_tax_domain = speedy["purchase_vat_tax_domain"] + [
            ("fr_vat_autoliquidation", "=", "partial"),
            ("amount", "<", 10.01),
            ("amount", ">", 9.99),
        ]
        candidate_taxes = speedy["at_obj"].search(candidate_royalty_tax_domain)
        royalty_purchase_tax = False
        due_vat_account = False
        for candidate_tax in candidate_taxes:
            rate_int = int(round(candidate_tax.amount * 10))
            regular_inv_lines = candidate_tax.invoice_repartition_line_ids.filtered(
                lambda x: x.repartition_type == "tax"
                and x.account_id
                and int(round(x.factor_percent)) == 100
            )
            neg92_inv_lines = candidate_tax.invoice_repartition_line_ids.filtered(
                lambda x: x.repartition_type == "tax"
                and x.account_id
                and int(round(x.factor_percent)) == -92
            )
            if (
                len(regular_inv_lines) == 1
                and len(neg92_inv_lines) == 1
                and rate_int == 100
            ):
                royalty_purchase_tax = candidate_tax
                due_vat_account = neg92_inv_lines.account_id
                if (
                    due_vat_account in speedy["autoliq_vat_account2rate"]
                    or due_vat_account in speedy["france_due_vat_accounts"]
                ):
                    raise UserError(
                        _(
                            "Account '%(account)s' is used as due VAT account on "
                            "royalty autoliquidation tax '%(tax)s', but "
                            "also in other taxes. This is not allowed by the OCA "
                            "VAT return module for France.",
                            account=due_vat_account.display_name,
                            tax=royalty_purchase_tax.with_context(
                                append_type_to_tax_name=True
                            ).display_name,
                        )
                    )

                break
        if royalty_purchase_tax:
            logger.info(
                "Royalty 10%%/9,2%% autoliq purchase VAT tax: %s. Due VAT account %s",
                royalty_purchase_tax.display_name,
                due_vat_account.display_name,
            )
            speedy["autoliq_vat_account2rate"][due_vat_account] = 920
            speedy["autoliq_tax2rate"][royalty_purchase_tax] = 920
            speedy["autoliq_taxedop_type2accounts"]["france"] |= due_vat_account
        else:
            logger.info("No royalty autoliq purchase VAT tax found")

    def manual2auto(self):
        self.ensure_one()
        assert self.state == "manual"
        speedy = self._prepare_speedy()
        action = self._setup_data_pre_check(speedy)
        if action:
            return action
        self._delete_move_and_attachments()  # should not be necessary at that step
        self._generate_operation_untaxed(speedy)
        self._generate_due_vat(speedy)
        self._generate_deductible_vat(speedy)
        self._generate_negative_boxes(speedy)
        self._adjustment_sum_due_vat_base_vs_taxed_operations(speedy)
        self._generate_credit_deferment(speedy)
        self._create_push_lines("start", speedy)
        self._generate_ca3_bottom_totals(speedy)
        self._create_sections(speedy)
        move = self._create_draft_account_move(speedy)
        self.write(
            {
                "state": "auto",
                "move_id": move.id,
            }
        )

    def back_to_manual(self):
        self.ensure_one()
        assert self.state in ("auto", "sent")
        self.autoliq_line_ids.unlink()
        # del auto lines
        self.line_ids.filtered(lambda x: not x.box_manual).unlink()
        self._delete_move_and_attachments()
        vals = {
            "state": "manual",
            "ignore_draft_moves": False,
            "autoliq_manual_done": False,
            "vat_credit_total": False,
        }
        if self.reimbursement_type:
            vals.update(self._prepare_remove_credit_vat_reimbursement())
        self.write(vals)

    def _delete_move_and_attachments(self):
        self.ensure_one()
        if self.move_id:
            if self.move_id.state == "posted":
                raise UserError(
                    _(
                        "The journal entry '%s' generated by the VAT return "
                        "cannot be deleted because it is already posted.",
                        self.move_id.display_name,
                    )
                )
            self.move_id.unlink()
        if self.ca3_attachment_id:
            self.ca3_attachment_id.unlink()
        if self.deductible_vat_zip_file_id:
            self.deductible_vat_zip_file_id.unlink()

    def auto2sent_manual(self):
        self.ensure_one()
        self.message_post(
            body=Markup(
                _("This VAT return has been <strong>manually marked as sent</strong>.")
            )
        )
        self._auto2sent()

    def _auto2sent(self, gateway_attachment_id=False):
        self.ensure_one()
        assert self.state == "auto"
        if not self.ca3_attachment_id:  # for archive
            self.generate_ca3_attachment()
        self.write(
            {
                "state": "sent",
                "sent_datetime": fields.Datetime.now(),
                "gateway_attachment_id": gateway_attachment_id,
            }
        )

    def sent2manual(self):
        self.ensure_one()
        assert self.state == "sent"
        self.write(
            {
                "state": "manual",
            }
        )

    def sent2posted(self):
        self.ensure_one()
        assert self.state == "sent"
        speedy = self._prepare_speedy()
        move = self.move_id
        if not move:
            raise UserError(_("The Journal Entry of this VAT return has been deleted."))
        if move.state == "cancel":
            raise UserError(
                _(
                    "The Journal Entry of this VAT return has been cancelled. "
                    "You should set it back to draft."
                )
            )
        if move.state == "draft":
            move.action_post()
        self._reconcile_account_move(speedy)
        if self.company_id.fr_vat_update_lock_dates and (
            not self.company_id.period_lock_date
            or (
                self.company_id.period_lock_date
                and self.company_id.period_lock_date < self.end_date
            )
        ):
            self.sudo().company_id.write({"period_lock_date": self.end_date})
        self.write({"state": "posted"})

    def _check_tax_invoice_refund_symmetry(self, speedy):
        for tax in self.env["account.tax"].search(speedy["company_domain"]):
            lines = []
            for iline in tax.invoice_repartition_line_ids:
                lines.append(
                    {
                        "account_id": iline.account_id or False,
                        "repartition_type": iline.repartition_type,
                        "factor_percent": iline.factor_percent,
                    }
                )
            error_msg = _(
                "Tax '%(tax)s' is not symetric between distribution for invoices "
                "and distribution for refunds.",
                tax=tax.with_context(append_type_to_tax_name=True).display_name,
            )
            if len(tax.refund_repartition_line_ids) != len(lines):
                raise UserError(error_msg)
            for rline in tax.refund_repartition_line_ids:
                if (
                    lines[0]["account_id"] != (rline.account_id or False)
                    or lines[0]["repartition_type"] != rline.repartition_type
                    or float_compare(
                        lines[0]["factor_percent"],
                        rline.factor_percent,
                        precision_digits=2,
                    )
                ):
                    raise UserError(error_msg)
                lines.pop(0)

    def _setup_data_pre_check(self, speedy):
        self.ensure_one()
        company = self.company_id
        self._check_tax_invoice_refund_symmetry(speedy)
        # Block if move of previous VAT return is in draft
        previous_vat_return = self.search(
            speedy["company_domain"] + [("start_date", "<", self.start_date)],
            limit=1,
            order="start_date desc",
        )
        if (
            previous_vat_return
            and previous_vat_return.move_id
            and previous_vat_return.move_id.state == "draft"
        ):
            raise UserError(
                _(
                    "The journal entry of the previous VAT return '%s' is in draft. "
                    "You must post it before continuing to process this VAT return "
                    "(or cancel it if you encoded and posted the journal entry of "
                    "the previous VAT return manually).",
                    previous_vat_return.display_name,
                )
            )
        # Warn if there are draft moves before end_date (block if option
        # 'Update Lock Date upon VAT Return Validation' is enabled)
        draft_moves = speedy["am_obj"].search(
            [("date", "<=", self.end_date), ("state", "=", "draft")]
            + speedy["company_domain"]
        )
        if draft_moves:
            if company.fr_vat_update_lock_dates:
                raise UserError(
                    _(
                        "There is/are %(count)d draft journal entry/entries "
                        "dated before %(date)s. You should post it/them, "
                        "delete it/them or postpone it/them.",
                        count=len(draft_moves),
                        date=format_date(self.env, self.end_date),
                    )
                )
            elif not self.ignore_draft_moves:
                action = self.env["ir.actions.actions"]._for_xml_id(
                    "l10n_fr_account_vat_return.l10n_fr_vat_draft_move_option_action"
                )
                action["context"] = dict(
                    self._context,
                    default_draft_move_ids=draft_moves.ids,
                    default_draft_move_count=len(draft_moves),
                    default_fr_vat_return_id=self.id,
                )
                return action
        if speedy["native_vat_on_payment"]:
            if not company.tax_cash_basis_journal_id:
                raise UserError(
                    _(
                        "Company %(company)s is configured to use the native "
                        "VAT on payment, but its Cash Basis Journal is not set.",
                        company=company.display_name,
                    )
                )
            purchase_on_payment_tax_count = speedy["at_obj"].search_count(
                speedy["company_domain"]
                + [
                    ("tax_exigibility", "=", "on_payment"),
                    ("type_tax_use", "=", "purchase"),
                ]
            )
            if not purchase_on_payment_tax_count:
                raise UserError(
                    _(
                        "Company %(company)s is configured to use the native "
                        "VAT on payment, but there is no purchase tax with "
                        "'Tax Exigibility' set to 'Based on Payment'.",
                        company=company.display_name,
                    )
                )
        else:
            if company.tax_cash_basis_journal_id:
                raise UserError(
                    _(
                        "Company %(company)s has a Cash Basis Journal '%(journal)s', "
                        "although the company is configured for non-native "
                        "VAT on payment.",
                        company=company.display_name,
                        journal=company.tax_cash_basis_journal_id.display_name,
                    )
                )
            on_payment_taxes_count = speedy["at_obj"].search_count(
                speedy["company_domain"] + [("tax_exigibility", "=", "on_payment")]
            )
            if on_payment_taxes_count:
                raise UserError(
                    _(
                        "There are still %(count)s On Payment tax(es) in company "
                        "'%(company)s', although the company is configured for "
                        "non-native VAT on payment.",
                        count=on_payment_taxes_count,
                        company=company.display_name,
                    )
                )
        action = self._generate_autoliq_lines(speedy)
        return action

    def _generate_autoliq_lines(self, speedy):  # noqa: C901
        self.ensure_one()
        action = False
        if self.autoliq_manual_done:
            return action
        elif self.autoliq_line_ids:
            self.autoliq_line_ids.unlink()

        default_option = (
            self.company_id.fr_vat_manual_autoliq_line_default_option or False
        )
        for autoliq_type in ("intracom", "extracom"):
            autoliq_vat_move_lines = speedy["aml_obj"].search(
                [
                    (
                        "account_id",
                        "in",
                        speedy["autoliq_taxedop_type2accounts"][autoliq_type].ids,
                    ),
                    ("balance", "!=", 0),
                    ("full_reconcile_id", "=", False),
                ]
                + speedy["base_domain_end"]
            )
            for line in autoliq_vat_move_lines:
                if line.journal_id.type == "sale":
                    raise UserError(
                        _(
                            "The journal item '%(line)s' has the autoliquidation "
                            "VAT account '%(account)s' and is in the sale journal "
                            "'%(journal)s'. Autoliquidation VAT accounts should "
                            "never be found in sale journals.",
                            line=line.display_name,
                            account=line.account_id.display_name,
                            journal=line.journal_id.display_name,
                        )
                    )
                total = 0.0
                product_subtotal = 0.0
                move = line.move_id
                rate_int = speedy["autoliq_vat_account2rate"][line.account_id]
                is_invoice = move.is_invoice()
                if is_invoice:
                    other_lines = move.invoice_line_ids.filtered(
                        lambda x: x.display_type == "product"
                    )
                else:
                    other_lines = speedy["aml_obj"]
                    for oline in move.line_ids:
                        if (
                            oline.id != line.id
                            and oline.account_id.account_type.startswith("expense")
                        ):
                            other_lines |= oline
                for oline in other_lines:
                    for tax in oline.tax_ids:
                        if (
                            tax in speedy["autoliq_tax2rate"]
                            and speedy["autoliq_tax2rate"][tax] == rate_int
                        ):
                            total += oline.balance
                            product_or_service = oline._fr_is_product_or_service()
                            if product_or_service == "product":
                                product_subtotal += oline.balance
                            break
                vals = {
                    "parent_id": self.id,
                    "move_line_id": line.id,
                    "autoliq_type": autoliq_type,
                    "vat_rate_int": rate_int,
                }
                if speedy["currency"].is_zero(total):
                    vals["compute_type"] = "manual"
                    if self.env.context.get("fr_vat_remind_auto_generate_and_transmit"):
                        vals["product_ratio"] = default_option == "product" and 100 or 0
                    autoliq_line = speedy["autoliq_line_obj"].create(vals)
                    if not action:
                        action = self.env["ir.actions.actions"]._for_xml_id(
                            "l10n_fr_account_vat_return.l10n_fr_vat_autoliq_manual_action"
                        )
                        action["context"] = {
                            "default_fr_vat_return_id": self.id,
                            "default_line_ids": [],
                        }
                    action["context"]["default_line_ids"].append(
                        Command.create(
                            {
                                "autoliq_line_id": autoliq_line.id,
                                "option": default_option,
                            }
                        )
                    )
                else:
                    vals.update(
                        {
                            "compute_type": "auto",
                            "product_ratio": round(100 * product_subtotal / total, 2),
                        }
                    )
                    speedy["autoliq_line_obj"].create(vals)
        if self.env.context.get("fr_vat_remind_auto_generate_and_transmit"):
            action = False
        return action

    def _generate_ca3_bottom_totals(self, speedy):
        # Process the END of CA3 by hand
        # Delete no_push_total_*, vat_total_debit and end_total_* lines
        # it corresponds to the 5 sum boxes at the bottom block of CA3
        lines_to_del = speedy["line_obj"].search(
            [
                ("parent_id", "=", self.id),
                (
                    "box_meaning_id",
                    "in",
                    (
                        "no_push_total_debit",
                        "no_push_total_credit",
                        "vat_total_debit",
                        "end_total_debit",
                        "end_total_credit",
                    ),
                ),
            ]
        )
        lines_to_del.unlink()

        # Generate the 'no_push_total_xxx' lines:
        # 25. Crédit de TVA (lignes 23 - 16)
        # 28. TVA nette due (lignes 16 - 23)
        vat_to_pay_line = speedy["line_obj"].search(
            [("parent_id", "=", self.id), ("box_meaning_id", "=", "due_vat_total")]
        )
        vat_to_pay = vat_to_pay_line and vat_to_pay_line.value or 0

        vat_deduc_line = speedy["line_obj"].search(
            [
                ("parent_id", "=", self.id),
                ("box_meaning_id", "=", "deductible_vat_total"),
            ]
        )
        vat_deduc = vat_deduc_line and vat_deduc_line.value or 0
        logs = [
            {
                "compute_type": "box",
                "amount": vat_to_pay,
                "note": vat_to_pay_line.box_id.display_name,
            },
            {
                "compute_type": "box",
                "amount": -vat_deduc,
                "note": vat_deduc_line.box_id.display_name,
            },
        ]
        sub_total = vat_to_pay - vat_deduc
        energy_vat_credit_line = speedy["line_obj"].search(
            [("parent_id", "=", self.id), ("box_meaning_id", "=", "energy_vat_credit")]
        )
        energy_vat_credit = energy_vat_credit_line and energy_vat_credit_line.value or 0
        if sub_total > 0:
            box = speedy["meaning_id2box"]["no_push_total_debit"]
            if sub_total < energy_vat_credit:
                raise UserError(
                    _(
                        "The amount of cell X4 (Crédit d'accise sur les énergies "
                        "imputé à la TVA) is %(energy_vat_credit)s €, "
                        "but the VAT to pay amount is only %(sub_total)s €.",
                        energy_vat_credit=formatLang(
                            self.env, energy_vat_credit, digits=0
                        ),
                        sub_total=formatLang(self.env, sub_total, digits=0),
                    )
                )
        else:
            box = speedy["meaning_id2box"]["no_push_total_credit"]
            if energy_vat_credit > 0:
                raise UserError(
                    _(
                        "The amount of cell X4 (Crédit d'accise sur les énergies "
                        "imputé à la TVA) is %(energy_vat_credit)s €, "
                        "but there is no VAT to pay (cell TD).",
                        energy_vat_credit=formatLang(
                            self.env, energy_vat_credit, digits=0
                        ),
                    )
                )
            for log in logs:
                log["amount"] *= -1
            self.write({"vat_credit_total": sub_total * -1})
        if box.accounting_method:  # True for no_push_total_debit
            account_id = self._get_box_account(box).id
            for log in logs:
                log["account_id"] = account_id
        speedy["line_obj"].create(
            {
                "parent_id": self.id,
                "box_id": box.id,
                "log_ids": [Command.create(x) for x in logs],
            }
        )
        # Generate push lines for the very bottom of CA3
        self._create_push_lines("end", speedy)

    def _push_lines_update_new_log_lines(
        self, new_log_lines, cur_amount, box, push_box, push_rate
    ):
        if float_is_zero(push_rate, precision_digits=PUSH_RATE_PRECISION):
            # simple sum boxes
            amount = cur_amount
            note = _("%s (add)", box.display_name)
        else:
            # rate push boxes that can be found in 3310A
            amount = int(round(push_rate * cur_amount / 100))
            note = f"{push_rate} % x " f"{cur_amount} €, " f"{box.display_name}"
        # prepare new log line
        account_id = False
        if push_box.accounting_method:
            account_id = self._get_box_account(push_box).id

        new_log_lines[push_box].append(
            Command.create(
                {
                    "compute_type": "box",
                    "note": note,
                    "amount": amount,
                    "account_id": account_id,
                }
            )
        )

    def _create_push_lines(self, pass_type, speedy):
        # only boxes at the bottom of CA3 have a push_sequence >= 100
        assert pass_type in ("start", "end")
        if pass_type == "start":
            box_domain = [("push_sequence", "<", 100)]
        elif pass_type == "end":
            box_domain = [("push_sequence", ">=", 100)]
        sequences = {}  # to have a list of unique push_sequence
        boxes = speedy["box_obj"].search(
            box_domain + [("push_box_id", "!=", False)], order="push_sequence"
        )
        for box in boxes:
            sequences[box.push_sequence] = True

        to_push_lines_base_domain = [
            ("parent_id", "=", self.id),
            ("box_push_box_id", "!=", False),
        ]
        cur_amount_domain = [
            ("parent_id", "=", self.id),
            ("box_edi_type", "=", "MOA"),
        ]

        for push_seq in sequences.keys():
            # Get lines that must generate/update a new line
            to_push_lines = speedy["line_obj"].search(
                [("box_push_sequence", "=", push_seq)] + to_push_lines_base_domain
            )
            new_log_lines = defaultdict(list)  # key = box, value = list of logs lines
            # get current value for all current boxes
            cur_amounts = {}  # key = box_id, value = amount (int)
            for line in speedy["line_obj"].search(cur_amount_domain):
                cur_amounts[line.box_id.id] = line.value  # integer
            for to_push_line in to_push_lines:
                box = to_push_line.box_id
                cur_amount = cur_amounts[box.id]
                self._push_lines_update_new_log_lines(
                    new_log_lines, cur_amount, box, box.push_box_id, box.push_rate
                )
                if box.push_box_2_id:
                    self._push_lines_update_new_log_lines(
                        new_log_lines,
                        cur_amount,
                        box,
                        box.push_box_2_id,
                        box.push_rate_2,
                    )

            # Create new lines
            for box, new_log_lines_list in new_log_lines.items():
                speedy["line_obj"].create(
                    {
                        "parent_id": self.id,
                        "box_id": box.id,
                        "log_ids": new_log_lines_list,
                    }
                )

    def _generate_credit_deferment(self, speedy):
        box = speedy["meaning_id2box"]["credit_deferment"]
        account = self._get_box_account(box)
        balance = account._fr_vat_get_balance("base_domain_end", speedy)
        # Check that the balance of 445670 is an integer
        if speedy["currency"].compare_amounts(balance, int(balance)):
            raise UserError(
                _(
                    "The balance of account '%(account)s' is %(balance)s. "
                    "In France, it should be a integer amount.",
                    account=account.display_name,
                    balance=format_amount(self.env, balance, speedy["currency"]),
                )
            )
        # Check that the balance of 445670 is the right sign
        compare_bal = speedy["currency"].compare_amounts(balance, 0)
        if compare_bal < 0:
            raise UserError(
                _(
                    "The balance of account '%(account)s' is %(balance)s. "
                    "It should always be positive or null.",
                    account=account.display_name,
                    balance=format_amount(self.env, balance, speedy["currency"]),
                )
            )
        elif compare_bal > 0:
            speedy["line_obj"].create(
                {
                    "parent_id": self.id,
                    "box_id": box.id,
                    "log_ids": [
                        Command.create(
                            {
                                "account_id": account.id,
                                "compute_type": "balance",
                                "amount": balance,
                            }
                        )
                    ],
                }
            )

    def _adjustment_box2value(self, speedy, boxes):
        box2value = {}
        total = 0
        box_codes = []
        for box in boxes:
            value = speedy["box2value"].get(box, 0)
            box2value[box] = value
            total += value
            box_codes.append(box.code)
        box_codes_str = ", ".join(box_codes)
        return box2value, total, box_codes_str

    def _adjustment_sum_due_vat_base_vs_taxed_operations(self, speedy):
        self.ensure_one()
        for vat_group in speedy["vat_groups"]:
            taxed_op_boxes = [
                box
                for meaning_id, box in speedy["meaning_id2box"].items()
                if meaning_id.startswith(f"taxed_op_{vat_group}")
            ]

            taxed_op_res = self._adjustment_box2value(speedy, taxed_op_boxes)
            taxed_op_box2value, taxed_op_sum, taxed_op_codes_str = taxed_op_res
            due_vat_base_boxes = [
                box.due_vat_base_box_id
                for meaning_id, box in speedy["meaning_id2box"].items()
                if meaning_id.startswith(f"due_vat_{vat_group}")
            ]
            due_vat_base_res = self._adjustment_box2value(speedy, due_vat_base_boxes)
            (
                due_vat_base_box2value,
                due_vat_base_sum,
                due_vat_base_codes_str,
            ) = due_vat_base_res
            assert isinstance(taxed_op_sum, int)
            assert isinstance(due_vat_base_sum, int)
            diff = due_vat_base_sum - taxed_op_sum
            assert isinstance(diff, int)
            if abs(diff) > 5:
                raise UserError(
                    _(
                        "There is a difference of %(diff)s € between "
                        "taxed operation boxes %(taxed_op_boxes)s and "
                        "due VAT base boxes %(due_vat_boxes)s. "
                        "The difference should be null or just a few euros. "
                        "This should never happen.",
                        diff=diff,
                        taxed_op_boxes=taxed_op_codes_str,
                        due_vat_boxes=due_vat_base_codes_str,
                    )
                )
            elif not diff:
                logger.debug(
                    "No need for adjustment line for boxes %s vs %s",
                    taxed_op_boxes,
                    due_vat_base_boxes,
                )
            else:
                logger.debug(
                    "Creating an adjustment log line for consistency check %s vs %s",
                    taxed_op_codes_str,
                    due_vat_base_codes_str,
                )
                max_taxed_op_box = max(taxed_op_box2value, key=taxed_op_box2value.get)
                note = _(
                    "Adjustment to have "
                    "sum of taxed operations boxes %(taxed_op_boxes)s = "
                    "sum of due VAT base boxes %(due_vat_boxes)s. "
                    "Otherwise, DGFiP would reject the VAT return.",
                    taxed_op_boxes=taxed_op_codes_str,
                    due_vat_boxes=due_vat_base_codes_str,
                )
                logs_to_add = [
                    {"compute_type": "adjustment", "amount": diff, "note": note}
                ]
                self._update_line(speedy, logs_to_add, max_taxed_op_box)
                new_taxed_op_sum = sum(
                    [
                        speedy["box2value"].get(box, 0)
                        for box in taxed_op_box2value.keys()
                    ]
                )
                assert new_taxed_op_sum == due_vat_base_sum

    def _generate_due_vat(self, speedy):
        self.ensure_one()
        # COMPUTE LINES
        type_rate2logs = {
            "regular_intracom_product_autoliq": defaultdict(list),
            "regular_intracom_service_autoliq": defaultdict(list),
            "extracom_product_autoliq": defaultdict(list),
            "regular_extracom_service_autoliq": defaultdict(list),
            "regular_france_autoliq": defaultdict(list),
            "regular_france": defaultdict(list),
            # 'regular_france': {2000: {'vat': [logs], 1000: [logs], 550: [], 'base': [logs]}
            # I put regular_france at the end, so that intracom/extracom autoliq
            # logs are not hidden at the end of the long list of unpaid_vat_on_payment logs
        }

        # Compute France and Monaco
        monaco_logs = self._generate_due_vat_france(speedy, type_rate2logs)
        # Compute Autoliquidation extracom + intracom + france (BTP subcontracting)
        self._generate_due_vat_autoliq(speedy, type_rate2logs)

        # CREATE LINES
        # Boxes 08, 09, 9B
        self._generate_taxed_op_and_due_vat_lines(speedy, type_rate2logs)
        # Box 17 "dont TVA sur acquisitions intracom"
        # generate autoliq_intracom_product_logs from type_rate2logs
        autoliq_intracom_product_logs = []
        for rate, logs in type_rate2logs["regular_intracom_product_autoliq"].items():
            if rate != "base":
                autoliq_intracom_product_logs += logs
        self._create_line(
            speedy, autoliq_intracom_product_logs, "due_vat_intracom_product"
        )
        # Box 18 Dont TVA sur opérations à destination de Monaco
        self._create_line(speedy, monaco_logs, "due_vat_monaco")

    def _france_due_vat_prepare_speedy(self, speedy):
        # REGULAR SALE TAXES
        france_due_vat_account2rate = {}
        france_due_vat_accounts = speedy["aa_obj"]
        regular_due_vat_taxes = speedy["at_obj"].search(
            speedy["sale_regular_vat_tax_domain"]
        )
        for tax in regular_due_vat_taxes:
            invoice_lines = tax.invoice_repartition_line_ids.filtered(
                lambda x: x.repartition_type == "tax"
                and x.account_id
                and int(x.factor_percent) == 100
            )
            if len(invoice_lines) != 1:
                raise UserError(
                    _(
                        "Tax '%s' should have only one distribution line for "
                        "invoices configured with an account and with '100%% of tax'.",
                        tax.with_context(append_type_to_tax_name=True).display_name,
                    )
                )
            sale_vat_account = invoice_lines.account_id
            rate_int = int(round(tax.amount * 100))
            if (
                sale_vat_account in france_due_vat_account2rate
                and france_due_vat_account2rate[sale_vat_account] != rate_int
            ):
                raise UserError(
                    _(
                        "Account '%(account)s' is used on several sale VAT taxes "
                        "for different rates (%(rate1).2f%% and %(rate2).2f%%).",
                        account=sale_vat_account.display_name,
                        rate1=rate_int / 100,
                        rate2=france_due_vat_account2rate[sale_vat_account] / 100,
                    )
                )
            france_due_vat_account2rate[sale_vat_account] = rate_int
            france_due_vat_accounts |= sale_vat_account

        if not france_due_vat_accounts:
            raise UserError(
                _(
                    "There are no regular sale taxes with UNECE Tax Type set to 'VAT' "
                    "in company '%s'.",
                    self.company_id.display_name,
                )
            )
        speedy.update(
            {
                "france_due_vat_accounts": france_due_vat_accounts,
                "france_due_vat_account2rate": france_due_vat_account2rate,
            }
        )

    def _generate_due_vat_france(self, speedy, type_rate2logs):
        logger.debug(
            "france_due_vat_account2rate=%s", speedy["france_due_vat_account2rate"]
        )
        if not speedy["native_vat_on_payment"]:
            vat_on_payment_account2logs = self._vat_on_payment(
                "out", speedy["france_due_vat_accounts"].ids, speedy
            )
        # generate type_rate2logs['france']
        for sale_vat_account, rate_int in speedy["france_due_vat_account2rate"].items():
            # Start from balance of VAT account, then compute base
            balance = (
                sale_vat_account._fr_vat_get_balance("base_domain_end", speedy) * -1
            )
            logger.debug(
                "sale VAT account %s (rate %s), balance %s",
                sale_vat_account.code,
                rate_int,
                balance,
            )
            if not speedy["currency"].is_zero(balance):
                type_rate2logs["regular_france"][rate_int].append(
                    {
                        "account_id": sale_vat_account.id,
                        "compute_type": "balance",
                        "amount": balance,
                    }
                )
            if not speedy["native_vat_on_payment"]:
                # remove on_payment invoices unpaid on end_date for type_rate2logs
                type_rate2logs["regular_france"][
                    rate_int
                ] += vat_on_payment_account2logs[sale_vat_account]
        # MONACO
        monaco_logs = self._generate_due_vat_monaco(speedy)
        return monaco_logs

    def _generate_due_vat_autoliq(self, speedy, type_rate2logs):
        # Split product/service for intracom and extracom (not for france)
        autoliq_rate2product_ratio = {
            "intracom": {},  # {2000: {'total': 200.0, 'product_subtotal': 112.80}}
            "extracom": {},
        }
        for line in self.autoliq_line_ids:
            if line.vat_rate_int not in autoliq_rate2product_ratio[line.autoliq_type]:
                autoliq_rate2product_ratio[line.autoliq_type][
                    line.vat_rate_int
                ] = defaultdict(float)
            # If the implementation was perfect, we would not have to use abs() !
            # But, in the current implementation, we take the balance of the autoliq VAT
            # account and we apply a product ratio. With this implementation, we don't
            # handle the case where autoliq product > 0 and autoliq service < 0
            # (or the opposite) which would require a special treatment.
            # abs() introduces a distortion when we have positive and negative amounts
            # in the autoliq lines. But, if we don't use it, we can have a ratio > 100
            balance = abs(line.move_line_id.balance)
            autoliq_rate2product_ratio[line.autoliq_type][line.vat_rate_int][
                "total"
            ] += balance
            autoliq_rate2product_ratio[line.autoliq_type][line.vat_rate_int][
                "product_subtotal"
            ] += speedy["currency"].round(balance * line.product_ratio / 100)
        # autoliq_intracom_product_logs = []  # for box 17
        # Compute both block B and block A for autoliq intracom + extracom
        for autoliq_type, accounts in speedy["autoliq_taxedop_type2accounts"].items():
            # autoliq_type is 'intracom', 'extracom' or 'france'
            for account in accounts:
                total_vat_amount = (
                    account._fr_vat_get_balance("base_domain_end", speedy) * -1
                )
                if speedy["currency"].is_zero(total_vat_amount):
                    continue
                rate_int = speedy["autoliq_vat_account2rate"][account]
                if autoliq_type == "france":
                    vat_log = {
                        "account_id": account.id,
                        "compute_type": "balance",
                        "amount": total_vat_amount,
                    }
                    type_rate2logs["regular_france_autoliq"][rate_int].append(vat_log)
                    continue
                # If you have a small residual amount in intracom/extracom autoliq accounts
                # and you set it to 0 with a write-off at a date after the VAT period, you
                # have 0 unreconciled move lines, but total_vat_amount != 0
                # In such a corner case, there is not rate_int key in
                # autoliq_rate2product_ratio[autoliq_type]
                # => we consider product_ratio = 0% and service_ratio = 100%
                product_ratio = 0
                if rate_int in autoliq_rate2product_ratio[autoliq_type]:
                    rate_data = autoliq_rate2product_ratio[autoliq_type][rate_int]
                    product_ratio = round(
                        100 * rate_data["product_subtotal"] / rate_data["total"], 2
                    )
                    assert float_compare(product_ratio, 100, precision_digits=2) <= 0
                    assert float_compare(product_ratio, 0, precision_digits=2) >= 0
                else:
                    logger.warning(
                        "rate_int %s not in autoliq_rate2product_ratio[%s]. "
                        "This can happen only in a very rare scenario.",
                        rate_int,
                        autoliq_type,
                    )
                ratio = {
                    "product": product_ratio,
                    "service": 100 - product_ratio,
                }
                product_vat_amount = round(total_vat_amount * product_ratio / 100, 2)
                ps_vat_amount = {
                    "product": product_vat_amount,
                    "service": total_vat_amount - product_vat_amount,
                }
                for ps_type in ["product", "service"]:
                    vat_amount = ps_vat_amount[ps_type]
                    if speedy["currency"].is_zero(vat_amount):
                        continue
                    ptype = f"regular_{autoliq_type}_{ps_type}_autoliq"
                    if ptype == "regular_extracom_product_autoliq":
                        ptype = "extracom_product_autoliq"
                    # Block B
                    # For proper translation in other languges, product/service
                    # cannot be a variable in the note field
                    if ps_type == "product":
                        vat_note = _(
                            "VAT amount %(total_vat_amount)s, "
                            "Product ratio %(ratio).2f%% "
                            "→ Product VAT amount %(vat_amount)s",
                            total_vat_amount=format_amount(
                                self.env, total_vat_amount, speedy["currency"]
                            ),
                            ratio=ratio[ps_type],
                            vat_amount=format_amount(
                                self.env, vat_amount, speedy["currency"]
                            ),
                        )
                    elif ps_type == "service":
                        vat_note = _(
                            "VAT amount %(total_vat_amount)s, "
                            "Service ratio %(ratio).2f%% "
                            "→ Service VAT amount %(vat_amount)s",
                            total_vat_amount=format_amount(
                                self.env, total_vat_amount, speedy["currency"]
                            ),
                            ratio=ratio[ps_type],
                            vat_amount=format_amount(
                                self.env, vat_amount, speedy["currency"]
                            ),
                        )

                    vat_log = {
                        "account_id": account.id,
                        "compute_type": "balance_ratio",
                        "amount": vat_amount,
                        "note": vat_note,
                    }
                    type_rate2logs[ptype][rate_int].append(vat_log)

    def _generate_taxed_op_and_due_vat_lines(self, speedy, type_rate2logs):
        # Create boxes 08, 09, 9B (columns base HT et Taxe due)
        vat_group_rate2box = {}
        for key_vat_group in speedy["vat_groups"]:
            vat_group_rate2box[key_vat_group] = {}  # {2000: box_rec, 1000, box_rec}
        for vat_group in vat_group_rate2box.keys():
            boxes = speedy["box_obj"].search(
                [
                    ("meaning_id", "=like", f"due_vat_{vat_group}_%"),
                    ("due_vat_rate", ">", 0),
                    ("due_vat_base_box_id", "!=", False),
                ]
            )
            for box in boxes:
                vat_group_rate2box[vat_group][int(box.due_vat_rate)] = box

        box2logs = defaultdict(list)
        # Prepare box2logs for Block A and Block B VAT amounts
        for ptype, rate2logs in type_rate2logs.items():
            for rate_int, logs in rate2logs.items():
                if not logs:
                    continue
                assert isinstance(rate_int, int)
                total_vat_amount = sum([log["amount"] for log in logs])
                vat_group = False
                for key_vat_group in speedy["vat_groups"]:
                    if ptype.startswith(key_vat_group):
                        vat_group = key_vat_group
                assert vat_group
                # Generate Base
                base_logs = []
                for log in logs:
                    base_amount = speedy["currency"].round(
                        log["amount"] * 10000 / rate_int
                    )
                    note = _(
                        "%(start_note)s, Rate %(rate).2f%% → Base %(base_amount)s",
                        start_note=log.get(
                            "note",
                            _(
                                "VAT amount %s",
                                format_amount(
                                    self.env, log["amount"], speedy["currency"]
                                ),
                            ),
                        ),
                        rate=rate_int / 100,
                        base_amount=format_amount(
                            self.env, base_amount, speedy["currency"]
                        ),
                    )
                    compute_type = f"base_from_{log['compute_type']}"
                    base_logs.append(
                        dict(
                            log,
                            note=note,
                            compute_type=compute_type,
                            amount=base_amount,
                        )
                    )

                # NEGATIVE
                if speedy["currency"].compare_amounts(total_vat_amount, 0) < 0:
                    box2logs["negative_due_vat"] += logs
                    box2logs[f"negative_due_vat_{vat_group}"] += logs
                    # Base
                    box2logs["negative_taxed_op"] += base_logs

                # POSITIVE
                else:
                    box = vat_group_rate2box[vat_group][rate_int]
                    box2logs[box] += logs
                    box2logs[f"taxed_op_{ptype}"] += base_logs

        for box, logs in box2logs.items():
            line = self._create_line(speedy, logs, box)
            box_rec = line.box_id
            if box_rec.meaning_id and box_rec.meaning_id.startswith(
                ("due_vat_regular_", "due_vat_extracom_product_")
            ):
                rate_int = box_rec.due_vat_rate
                assert isinstance(rate_int, int)
                assert rate_int > 0
                base_amount = line.value_float * 10000 / rate_int
                log_base_vat = {
                    "compute_type": "rate",
                    "amount": base_amount,
                    "note": _(
                        "VAT amount %(vat_amount)s, Rate %(rate).2f%% → "
                        "Base %(base_amount)s",
                        vat_amount=format_amount(
                            self.env, line.value_float, speedy["currency"]
                        ),
                        rate=rate_int / 100,
                        base_amount=format_amount(
                            self.env, base_amount, speedy["currency"]
                        ),
                    ),
                }
                self._create_line(speedy, [log_base_vat], box_rec.due_vat_base_box_id)

    def _generate_due_vat_monaco(self, speedy):
        # Dont TVA sur opérations à destination de Monaco
        # WARNING This is fine if the company is VAT on debit,
        # but not exact when VAT on payment
        # If we want to have accurate support for Monaco with VAT on payment
        # we would need a dedicated 44571x account for Monaco (per rate)
        # and a dedicated fiscal position => probably not worth it
        mc_partners = self.env["res.partner"].search(
            [("country_id", "=", self.env.ref("base.mc").id), ("parent_id", "=", False)]
        )
        mc_mlines = speedy["aml_obj"].search(
            [
                ("partner_id", "in", mc_partners.ids),
                ("account_id", "in", speedy["france_due_vat_accounts"].ids),
                ("balance", "!=", 0),
            ]
            + speedy["base_domain_period_sale"]
        )
        monaco_box_logs = []
        for mline in mc_mlines:
            vat_amount = mline.balance * -1
            monaco_box_logs.append(
                {
                    "account_id": mline.account_id.id,
                    "compute_type": "computed_vat_amount",
                    "amount": vat_amount,
                    "origin_move_id": mline.move_id.id,
                    "note": _(
                        "%(invoice)s of customer %(partner)s from Monaco, "
                        "VAT amount %(vat_amount)s",
                        invoice=mline.move_id.name,
                        partner=mline.partner_id.display_name,
                        vat_amount=format_amount(
                            self.env, vat_amount, speedy["currency"]
                        ),
                    ),
                }
            )
        return monaco_box_logs

    def _create_line(self, speedy, logs, box, negative_box=None):
        """Box argument can be a meaning_id or a box"""
        line = False
        if logs:
            if isinstance(box, str):
                box = speedy["meaning_id2box"][box]
            if negative_box:
                total = sum([log["amount"] for log in logs])
                if speedy["currency"].compare_amounts(total, 0) < 0:
                    speedy["negative_box2logs"][negative_box] += logs
                    return False
            vals = {
                "parent_id": self.id,
                "box_id": box.id,
                "log_ids": [Command.create(x) for x in logs],
            }
            line = speedy["line_obj"].create(vals)
            speedy["box2value"][box] = line.value
        return line

    def _update_line(self, speedy, logs_to_add, box):
        line = speedy["line_obj"].search(
            [("box_id", "=", box.id), ("parent_id", "=", self.id)]
        )
        assert line
        if not isinstance(logs_to_add, list):
            logs_to_add = [logs_to_add]
        old_value = line.value
        line.write({"log_ids": [Command.create(vals) for vals in logs_to_add]})
        new_value = line.value
        speedy["box2value"][line.box_id] = new_value
        logger.info(
            "Update line with box %s: old value %s new value %s",
            box.display_name,
            old_value,
            new_value,
        )

    def _vat_on_payment(self, in_or_out, vat_account_ids, speedy):
        assert in_or_out in ("in", "out")
        account2logs = defaultdict(list)
        common_move_domain = speedy["company_domain"] + [
            ("date", "<=", self.end_date),
            ("amount_total", ">", 0),
            ("state", "=", "posted"),
        ]
        if in_or_out == "in":
            journal_type = "purchase"
            vat_sign = -1
            account_type = "liability_payable"
            vat_account_type = "asset_current"
            common_move_domain += [
                ("move_type", "in", ("in_invoice", "in_refund", "in_receipt")),
                ("fiscal_position_fr_vat_type", "=", "france_vendor_vat_on_payment"),
            ]
        elif in_or_out == "out":
            journal_type = "sale"
            vat_sign = 1
            account_type = "asset_receivable"
            vat_account_type = "liability_current"
            common_move_domain += [
                ("out_vat_on_payment", "=", True),
                ("move_type", "in", ("out_invoice", "out_refund", "out_receipt")),
                (
                    "fiscal_position_fr_vat_type",
                    "in",
                    (False, "france", "france_vendor_vat_on_payment"),
                ),
            ]
        # The goal of this method is to "remove" on_payment invoices that were unpaid
        # on self.end_date
        # Several cases :
        # 0) Manual lines. Designed to handle the first months of Odoo accounting
        # when we don't have any history of invoices in Odoo and we only imported the
        # start balance of accounts
        # 1) Unpaid invoices today:
        # if they are unpaid today, they were unpaid on end_date -> easy
        # 2) Partially paid invoices today:
        # they were unpaid or partially paid on end_date
        # Volume is low, we can analyse them one by one
        # 3) Paid and in_payment invoices today:
        # we want to find paid/in_payment invoices that were unpaid or partially
        # paid on end_date.
        # Volume is high, so it would be too lengthy to analyse all of them
        # => to detect those, we look at move lines with a full reconcile created
        # after end_date

        # Case 0. Manual VAT on payment lines
        for manual_line in self.unpaid_vat_on_payment_manual_line_ids:
            assert (
                manual_line.account_id.id
                in self.unpaid_vat_on_payment_manual_line_filter_account_ids.ids
            )
            if manual_line.account_id.account_type == vat_account_type and not speedy[
                "currency"
            ].is_zero(manual_line.amount):
                prefix = _("⚠ Manual line")
                if manual_line.note:
                    note = " - ".join([prefix, manual_line.note])
                else:
                    note = prefix
                account2logs[manual_line.account_id].append(
                    {
                        "note": note,
                        "amount": manual_line.amount * -1,
                        "account_id": manual_line.account_id.id,
                        "compute_type": "unpaid_vat_on_payment",
                    }
                )

        # Case 1. unpaid invoices
        unpaid_invs = speedy["am_obj"].search(
            common_move_domain + [("payment_state", "=", "not_paid")]
        )
        for unpaid_inv in unpaid_invs:
            for line in unpaid_inv.line_ids.filtered(
                lambda x: x.display_type == "tax" and x.account_id.id in vat_account_ids
            ):
                amount = speedy["currency"].round(line.balance) * vat_sign
                note = _(
                    "%(invoice)s (%(partner)s) is unpaid, "
                    "Unpaid VAT amount %(amount)s",
                    invoice=unpaid_inv.name,
                    partner=unpaid_inv.commercial_partner_id.display_name,
                    amount=format_amount(self.env, amount, speedy["currency"]),
                )
                account2logs[line.account_id].append(
                    {
                        "note": note,
                        "amount": amount,
                        "account_id": line.account_id.id,
                        "compute_type": "unpaid_vat_on_payment",
                        "origin_move_id": unpaid_inv.id,
                    }
                )
        # Case 2: partially paid invoices
        partially_paid_invs = speedy["am_obj"].search(
            common_move_domain + [("payment_state", "=", "partial")]
        )

        # Case 3: paid and in_payment invoices
        purchase_or_sale_journals = speedy["aj_obj"].search(
            speedy["company_domain"] + [("type", "=", journal_type)]
        )
        # won't work when the invoice is paid next month by a refund
        payable_or_receivable_accounts = speedy["aa_obj"].search(
            speedy["company_domain"] + [("account_type", "=", account_type)]
        )
        # I want reconcile marks after first day of current month
        # But, to avoid trouble with timezones, I use '>=' self.end_date (and not '>')
        # It's not a problem if we have few additionnal invoices to analyse
        full_reconcile_post_end = self.env["account.full.reconcile"].search(
            [("create_date", ">=", self.end_date)]
        )
        reconciled_purchase_or_sale_lines = speedy["aml_obj"].search(
            speedy["base_domain"]
            + [
                ("full_reconcile_id", "in", full_reconcile_post_end.ids),
                ("journal_id", "in", purchase_or_sale_journals.ids),
                ("date", "<=", self.end_date),
                ("account_id", "in", payable_or_receivable_accounts.ids),
                ("balance", "!=", 0),
            ]
        )
        # I do confirm that, if 2 moves lines in reconciled_purchase_or_sale_lines
        # are part of the same move, that move will be present only once
        # in paid_invoices_to_analyse (tested on v14)
        paid_invoices_to_analyse = speedy["am_obj"].search(
            common_move_domain
            + [
                ("payment_state", "in", ("paid", "in_payment", "reversed")),
                ("id", "in", reconciled_purchase_or_sale_lines.move_id.ids),
            ]
        )
        # Process case 2 and 3
        invoices_to_analyse = partially_paid_invs
        invoices_to_analyse |= paid_invoices_to_analyse
        for move in invoices_to_analyse:
            # compute unpaid_amount on end_date
            unpaid_amount = move.amount_total  # initialize value
            fully_unpaid = True
            pay_infos = (
                isinstance(move.invoice_payments_widget, dict)
                and move.invoice_payments_widget["content"]
                or []
            )
            for payment in pay_infos:
                if payment["date"] <= self.end_date and payment["amount"]:
                    unpaid_amount -= payment["amount"]
                    fully_unpaid = False
            # If invoice is not fully paid on end_date, compute an unpaid ratio
            if not move.currency_id.is_zero(unpaid_amount):
                unpaid_ratio = unpaid_amount / move.amount_total
                for line in move.line_ids.filtered(
                    lambda x: x.display_type == "tax"
                    and x.account_id.id in vat_account_ids
                ):
                    balance = line.balance * vat_sign
                    if fully_unpaid:
                        amount = speedy["currency"].round(balance)
                        note = _(
                            "%(invoice)s (%(partner)s) was unpaid on %(date)s, "
                            "Unpaid VAT amount %(amount)s",
                            invoice=move.name,
                            partner=move.commercial_partner_id.display_name,
                            date=speedy["end_date_formatted"],
                            amount=format_amount(self.env, amount, speedy["currency"]),
                        )
                    else:
                        amount = speedy["currency"].round(balance * unpaid_ratio)
                        note = _(
                            "%(unpaid_ratio)d%% of %(invoice)s (%(partner)s) "
                            "was unpaid on %(date)s, VAT amount %(total_vat_amount)s → "
                            "Unpaid VAT amount %(unpaid_vat_amount)s",
                            unpaid_ratio=int(round(unpaid_ratio * 100)),
                            invoice=move.name,
                            partner=move.commercial_partner_id.display_name,
                            date=speedy["end_date_formatted"],
                            total_vat_amount=format_amount(
                                self.env, balance, speedy["currency"]
                            ),
                            unpaid_vat_amount=format_amount(
                                self.env, amount, speedy["currency"]
                            ),
                        )

                    account2logs[line.account_id].append(
                        {
                            "note": note,
                            "amount": amount,
                            "account_id": line.account_id.id,
                            "compute_type": "unpaid_vat_on_payment",
                            "origin_move_id": move.id,
                        }
                    )
        return account2logs

    def _generate_deductible_vat(self, speedy):
        self.ensure_one()
        vat_account2type = self._generate_deductible_vat_prepare_struct(speedy)
        # vat_account2type is a dict with:
        # key = deduc VAT account
        # value = 'asset', 'regular' or 'autoliq'
        box_meaning_id2vat_accounts = {
            "deductible_vat_asset": [
                account
                for (account, vtype) in vat_account2type.items()
                if vtype == "asset"
            ],
            "deductible_vat_other": [
                account
                for (account, vtype) in vat_account2type.items()
                if vtype in ("autoliq", "regular")
            ],
        }

        vat_payment_deduc_accounts = speedy["aa_obj"]
        for account, vtype in vat_account2type.items():
            if vtype in ("asset", "regular"):
                vat_payment_deduc_accounts |= account

        if not speedy["native_vat_on_payment"]:
            # Generate logs for vat_on_payment supplier invoices
            vat_on_payment_account2logs = self._vat_on_payment(
                "in", vat_payment_deduc_accounts.ids, speedy
            )

        # Generate return line for the 2 deduc VAT boxes
        for box_meaning_id, vat_accounts in box_meaning_id2vat_accounts.items():
            logger.info(
                "Deduc VAT accounts: %s go to box meaning_id %s",
                ", ".join([x.code for x in vat_accounts]),
                box_meaning_id,
            )
            logs = []
            for vat_account in vat_accounts:
                # balance of deduc VAT account
                balance = vat_account._fr_vat_get_balance("base_domain_end", speedy)
                if not speedy["currency"].is_zero(balance):
                    logs.append(
                        {
                            "account_id": vat_account.id,
                            "compute_type": "balance",
                            "amount": balance,
                        }
                    )
                # minus unpaid vat_on_payment supplier invoices
                if not speedy["native_vat_on_payment"]:
                    logs += vat_on_payment_account2logs[vat_account]
            self._create_line(
                speedy, logs, box_meaning_id, negative_box="negative_deductible_vat"
            )

    def _generate_deductible_vat_prepare_struct(self, speedy):
        vat_account2type = {}
        # order is designed to have the autoliq log lines first, so that they are not after
        # the long list of VAT on payment log lines
        deduc_vat_taxes = speedy["at_obj"].search(
            speedy["purchase_vat_tax_domain"],
            order="fr_vat_autoliquidation, sequence",
        )
        for tax in deduc_vat_taxes:
            line = tax.invoice_repartition_line_ids.filtered(
                lambda x: x.repartition_type == "tax"
                and x.account_id
                and int(x.factor_percent) == 100
            )
            if len(line) != 1:
                logger.debug(
                    "Check that tax %s is a special gasoline tax", tax.display_name
                )
                continue
            vat_account = line.account_id
            if tax.fr_vat_autoliquidation:
                vtype = "autoliq"
            else:
                if vat_account.code.startswith("44562"):
                    vtype = "asset"
                else:
                    vtype = "regular"
                    if not vat_account.code.startswith("44566"):
                        logger.warning(
                            "Found regular deduc VAT account %s. "
                            "Very strange, it should start with 44566.",
                            vat_account.code,
                        )
            if (
                vat_account in vat_account2type
                and vat_account2type[vat_account] != vtype
            ):
                raise UserError(
                    _(
                        "Account '%(account)s' is used for several kinds of "
                        "deductible VAT taxes (%(type1)s and %(type2)s).",
                        account=vat_account.display_name,
                        type1=vtype,
                        type2=vat_account2type[vat_account],
                    )
                )
            vat_account2type[vat_account] = vtype

        logger.info(
            "Deduc VAT accounts: %s"
            % ", ".join(
                [f"{acc.code} ({vtype})" for (acc, vtype) in vat_account2type.items()]
            )
        )
        return vat_account2type

    def _generate_operation_untaxed(self, speedy):
        self.ensure_one()
        fp_types = ["intracom_b2b", "intracom_b2c", "extracom", "france_exo"]
        fpositions2box_meaning_id = {}
        for fp_type in fp_types:
            box_meaning_id = f"untaxed_op_{fp_type}"
            fpositions = speedy["afp_obj"].search(
                speedy["company_domain"] + [("fr_vat_type", "=", fp_type)]
            )
            fpositions2box_meaning_id[fpositions] = box_meaning_id
        sale_account_types = ["income", "income_other", "liability_current"]
        # liability_current added to include
        # 419100 Clients créditeurs - Avances et acomptes reçus sur commandes
        box_meaning_id2accounts = {}
        for fpositions, box_meaning_id in fpositions2box_meaning_id.items():
            for fposition in fpositions:
                revenue_account_mappings = fposition.account_ids.filtered(
                    lambda x: x.account_src_id.account_type in sale_account_types
                    and x.account_dest_id.account_type in sale_account_types
                )
                if not revenue_account_mappings:
                    if fposition.fr_vat_type == "france_exo":
                        # it may be a purchase-only fiscal position (ex: Auto-entrep)
                        # -> no raise, only write a warning in chatter
                        self.message_post(
                            body=_(
                                "No account mapping on fiscal position "
                                "<a href=# data-oe-model=account.fiscal.position "
                                "data-oe-id=%(fiscal_position_id)d>%(fiscal_position)s</a>. "
                                "If this fiscal position is not "
                                "only used for purchase but also for sale, you must "
                                "configure an account mapping on revenue accounts.",
                                fiscal_position_id=fposition.id,
                                fiscal_position=fposition.display_name,
                            )
                        )
                    else:
                        raise UserError(
                            _(
                                "Missing account mapping on fiscal position '%s'.",
                                fposition.display_name,
                            )
                        )
                for mapping in revenue_account_mappings:
                    if box_meaning_id not in box_meaning_id2accounts:
                        box_meaning_id2accounts[
                            box_meaning_id
                        ] = mapping.account_dest_id
                    else:
                        box_meaning_id2accounts[
                            box_meaning_id
                        ] |= mapping.account_dest_id
        # check that an account is not present in several fiscal positions
        # and create lines
        account_unicity = []
        for box_meaning_id, accounts in box_meaning_id2accounts.items():
            if account_unicity:
                for acc in accounts:
                    if acc.id in account_unicity:
                        raise UserError(
                            _(
                                "Account '%s' is present in the mapping of several "
                                "fiscal positions.",
                                acc.display_name,
                            )
                        )
            account_unicity += accounts.ids
            # create the declaration lines
            logs = []
            for account in accounts:
                balance = account._fr_vat_get_balance("base_domain_period_sale", speedy)
                if not speedy["currency"].is_zero(balance):
                    logs.append(
                        {
                            "amount": balance * -1,
                            "account_id": account.id,
                            "compute_type": "period_balance_sale",
                        }
                    )
            self._create_line(
                speedy, logs, box_meaning_id, negative_box="negative_untaxed_op"
            )

    def _generate_negative_boxes(self, speedy):
        for box, logs in speedy["negative_box2logs"].items():
            self._create_line(speedy, logs, box)

    def create_reimbursement_line(self, amount):
        assert isinstance(amount, int)
        assert amount > 0
        speedy = self._prepare_speedy()
        box = speedy["meaning_id2box"]["vat_reimbursement"]
        account_id = self._get_box_account(box).id
        log_vals = {
            "amount": amount,
            "compute_type": "manual",
            "account_id": account_id,
        }
        vals = {
            "box_id": box.id,
            "parent_id": self.id,
            "log_ids": [Command.create(log_vals)],
        }
        speedy["line_obj"].create(vals)
        self._generate_ca3_bottom_totals(speedy)

    def _prepare_remove_credit_vat_reimbursement(self):
        vals = {
            "reimbursement_type": False,
            "reimbursement_first_creation_date": False,
            "reimbursement_end_date": False,
            "reimbursement_comment_dgfip": False,
        }
        return vals

    def remove_credit_vat_reimbursement(self):
        self.ensure_one()
        speedy = self._prepare_speedy()
        self.message_post(body=_("Credit VAT Reimbursement removed."))
        line_to_delete = speedy["line_obj"].search(
            [("box_meaning_id", "=", "vat_reimbursement"), ("parent_id", "=", self.id)]
        )
        line_to_delete.unlink()
        self._generate_ca3_bottom_totals(speedy)
        self._delete_move_and_attachments()
        move = self._create_draft_account_move(speedy)
        vals = self._prepare_remove_credit_vat_reimbursement()
        vals["move_id"] = move.id
        self.write(vals)

    def _create_sections(self, speedy):
        # sections are created at the very end of generate_lines()
        # that way, we don't create sections for 3310A if there are not 3310A lines
        self.ensure_one()
        box_domain = [("display_type", "!=", False)]
        if not speedy["line_obj"].search_count(
            [("box_form_code", "=", "3310A"), ("parent_id", "=", self.id)]
        ):
            box_domain.append(("form_code", "!=", "3310A"))
        boxes = speedy["box_obj"].search(box_domain)
        speedy["line_obj"].create(
            [{"parent_id": self.id, "box_id": box.id} for box in boxes]
        )

    def _check_account_move_setup(self):
        self.ensure_one()
        if not self.company_id.fr_vat_journal_id:
            raise UserError(
                _(
                    "Journal for VAT Journal Entry is not set on company '%s'.",
                    self.company_id.display_name,
                )
            )
        if not self.company_id.l10n_fr_rounding_difference_loss_account_id:
            raise UserError(
                _(
                    "Expense account for rounding is not set on company '%s'.",
                    self.company_id.display_name,
                )
            )
        if not self.company_id.l10n_fr_rounding_difference_profit_account_id:
            raise UserError(
                _(
                    "Income account for rounding is not set on company '%s'.",
                    self.company_id.display_name,
                )
            )

    def _prepare_account_move(self, speedy):
        self.ensure_one()
        self._check_account_move_setup()
        lvals_list = []
        total = 0.0
        account2amount = defaultdict(float)
        for line in self.line_ids.filtered(lambda x: x.box_accounting_method):
            method = line.box_accounting_method
            sign = method == "credit" and 1 or -1
            if line.box_manual and line.value_manual_int:
                account = line.manual_account_id
                if not account:
                    raise UserError(
                        _(
                            "Account is missing on manual line '%s'.",
                            line.box_id.display_name,
                        )
                    )
                account2amount[
                    (account, json.dumps(line.manual_analytic_distribution))
                ] += (line.value_manual_int * sign)
            else:
                for log in line.log_ids:
                    assert log.account_id  # there is a python constrain on this
                    amount = log.amount * sign
                    # Special case for for VAT credit account 44567:
                    # we don't want to group
                    if log.account_id.code.startswith("44567"):
                        lvals = {
                            "account_id": log.account_id.id,
                            "analytic_distribution": log.analytic_distribution,
                        }
                        amount = speedy["currency"].round(amount)
                        total += amount
                        compare = speedy["currency"].compare_amounts(amount, 0)
                        if compare > 0:
                            lvals["credit"] = amount
                            lvals_list.append(lvals)
                        elif compare < 0:
                            lvals["debit"] = -amount
                            lvals_list.append(lvals)
                        logger.debug(
                            "VAT move account %s: %s", log.account_id.code, lvals
                        )
                    else:
                        account2amount[
                            (log.account_id, json.dumps(log.analytic_distribution))
                        ] += amount
        for (account, analytic_distribution_str), amount in account2amount.items():
            analytic_distribution = json.loads(analytic_distribution_str)
            amount = speedy["currency"].round(amount)
            total += amount
            compare = speedy["currency"].compare_amounts(amount, 0)
            lvals = {
                "account_id": account.id,
                "analytic_distribution": analytic_distribution,
            }
            if compare > 0:
                lvals["credit"] = amount
                lvals_list.append(lvals)
            elif compare < 0:
                lvals["debit"] = -amount
                lvals_list.append(lvals)
            logger.debug("VAT move account %s: %s", account.code, lvals)
        # On 1 due VAT or deductible VAT cell, the rounding effect can cause a gap of 0.50 €
        # between due/deduc VAT account and VAT to pay (or VAT credit)
        # We have 2 deduc VAT cells (immo and 5 regular) and 10 due VAT cells
        # (5 VAT rates x 2 for regular and import)
        if speedy["currency"].compare_amounts(abs(total), 0.5 * 12) > 0:
            raise UserError(
                _(
                    "Error in the generation of the journal entry: the adjustment amount "
                    "is %s. The ajustment is only needed because, in the VAT "
                    "journal entry, the amount of the VAT to pay (or VAT credit) is "
                    "rounded (because the amounts are rounded in the VAT return) "
                    "and the other amounts are not rounded."
                    "As a consequence, the amount of the adjustment should be under 6 €. "
                    "This error may be caused by a bad configuration of the "
                    "accounting method of some VAT boxes.",
                    format_amount(self.env, total, speedy["currency"]),
                )
            )
        company = self.company_id
        total_compare = speedy["currency"].compare_amounts(total, 0)
        total = speedy["currency"].round(total)
        if total_compare > 0:
            account_id = company.l10n_fr_rounding_difference_loss_account_id.id
            analytic_dist = company.fr_vat_expense_analytic_distribution
            lvals_list.append(
                {
                    "debit": total,
                    "account_id": account_id,
                    "analytic_distribution": analytic_dist,
                }
            )
        elif total_compare < 0:
            account_id = company.l10n_fr_rounding_difference_profit_account_id.id
            analytic_dist = company.fr_vat_income_analytic_distribution
            lvals_list.append(
                {
                    "credit": -total,
                    "account_id": account_id,
                    "analytic_distribution": analytic_dist,
                }
            )

        vals = {
            "date": self.end_date,
            "journal_id": self.company_id.fr_vat_journal_id.id,
            "ref": self.display_name,
            "company_id": speedy["company_id"],
            "line_ids": [Command.create(x) for x in lvals_list],
        }
        return vals

    def reconcile_account_move_button(self):
        self.ensure_one()
        speedy = self._prepare_speedy()
        if self.move_id.state != "posted":
            raise UserError(
                _(
                    "The journal entry '%s' is not posted, "
                    "so it is not possible to reconcile again.",
                    self.move_id.display_name,
                )
            )
        self._reconcile_account_move(speedy)

    def _reconcile_account_move(self, speedy):
        self.ensure_one()
        move = self.move_id
        assert move.state == "posted"
        excluded_lines = speedy["log_obj"].search_read(
            [
                ("parent_parent_id", "=", self.id),
                ("origin_move_id", "!=", False),
                ("compute_type", "=", "unpaid_vat_on_payment"),
            ],
            ["origin_move_id"],
        )
        excluded_line_ids = [x["origin_move_id"][0] for x in excluded_lines]
        # to allow reconciliation of 445670, we need to exclude the debit line
        # from the reconciliation to have a balance at 0
        credit_vat_account = self._get_box_account(
            speedy["meaning_id2box"]["credit_deferment"]
        )
        credit_vat_debit_mline = speedy["aml_obj"].search(
            [
                ("move_id", "=", move.id),
                ("account_id", "=", credit_vat_account.id),
                ("debit", ">", 0.9),
            ],
            limit=1,
        )
        success_account_codes = set()
        for line in move.line_ids.filtered(lambda x: x.account_id.reconcile):
            account = line.account_id
            domain = speedy["base_domain_end"] + [
                ("account_id", "=", account.id),
                ("reconciled", "=", False),
                ("full_reconcile_id", "=", False),
                ("move_id", "not in", excluded_line_ids),
            ]
            if account == credit_vat_account and credit_vat_debit_mline:
                domain.append(("id", "!=", credit_vat_debit_mline.id))
            rg_res = speedy["aml_obj"].read_group(domain, ["balance"], [])
            # or 0 is need to avoid a crash: rg_res[0]["balance"] = None
            # when the moves are already reconciled
            if rg_res and speedy["currency"].is_zero(rg_res[0]["balance"] or 0):
                moves_to_reconcile = speedy["aml_obj"].search(domain)
                if moves_to_reconcile:
                    moves_to_reconcile.remove_move_reconcile()
                    moves_to_reconcile.reconcile()
                    logger.info(
                        "Successful reconciliation in account %s", account.display_name
                    )
                    success_account_codes.add(account.code)
        if success_account_codes:
            sorted_account_codes = sorted(success_account_codes, key=lambda x: x[0])
            self.message_post(
                body=_(
                    "Successful reconciliation in accounts %s.",
                    ", ".join(sorted_account_codes),
                )
            )

    def generate_zip_deductible_vat(self):
        self.ensure_one()
        if self.deductible_vat_zip_file_id:
            self.deductible_vat_zip_file_id.unlink()
            chatter_msg = _("Deductible VAT ZIP file re-generated.")
        else:
            chatter_msg = _("Deductible VAT ZIP file generated.")
        speedy = self._prepare_speedy()
        vataccount2type = self._generate_deductible_vat_prepare_struct(speedy)
        account2rec = {}
        for line in self.move_id.line_ids:
            if line.full_reconcile_id and line.account_id in vataccount2type:
                account2rec[line.account_id] = line.full_reconcile_id
        if not account2rec:
            raise UserError(
                _(
                    "Odoo cannot generate the deductible VAT justification file "
                    "because the journal items with deductible VAT accounts of "
                    "the journal entry %(move)s are not reconciled.",
                    move=self.move_id.display_name,
                )
            )
        xlsx_fileobj = io.BytesIO()
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            workbook = xlsxwriter.Workbook(xlsx_fileobj)
            wdict = {
                "workbook": workbook,
                "zip_file": zip_file,
                "account2rec": account2rec,
                "move_id2filename": {},
                "styles": self._prepare_xlsx_styles(workbook),
                "coldict": self._prepare_xlsx_cols(),
            }
            asheet, aline = self._create_xlsx_sheet(
                "19-immos",
                "19. Biens constituant des immobilisations",
                wdict,
            )
            osheet, oline = self._create_xlsx_sheet(
                "20-ABS", "20. Autres biens et services", wdict
            )
            for account, vtype in vataccount2type.items():
                if vtype == "asset":
                    aline = self._zip_deductible_vat_process_account(
                        account, asheet, aline, wdict
                    )
                else:
                    oline = self._zip_deductible_vat_process_account(
                        account,
                        osheet,
                        oline,
                        wdict,
                        attach_threshold=self.deductible_vat_zip_other_threshold,
                    )
            workbook.close()
            zip_file.writestr(
                f"{self.name}-deduc_VAT_justif.xlsx", xlsx_fileobj.getvalue()
            )
        filename = self._prepare_zip_deductible_vat_filename()
        attach = self.env["ir.attachment"].create(
            {
                "name": filename,
                "raw": zip_buffer.getvalue(),
                "res_id": self.id,
                "res_model": self._name,
            }
        )
        self.write({"deductible_vat_zip_file_id": attach.id})
        self.message_post(body=chatter_msg)
        action = {
            "name": filename,
            "type": "ir.actions.act_url",
            "url": f"web/content/?model={self._name}&id={self.id}&"
            f"filename_field=deductible_vat_zip_file_name&field=deductible_vat_zip_file_datas&"
            f"download=true&filename={filename}",
            "target": "new",
            # target: "new" and NOT "self", otherwise you get the following bug:
            # after this action, all UserError won't show a pop-up to the user
            # but will only show a warning message in the logs until the web
            # page is reloaded
        }
        return action

    def _zip_deductible_vat_process_account(
        self, account, sheet, line, wdict, attach_threshold=None
    ):
        self.ensure_one()
        if account in wdict["account2rec"]:
            rec = wdict["account2rec"][account]
            for mline in rec.reconciled_line_ids:
                move = mline.move_id
                if move == self.move_id:
                    continue
                line += 1
                linedict = mline._prepare_xlsx_zip_deductible_vat(
                    wdict, attach_threshold=attach_threshold
                )
                self._write_xlsx_line(sheet, line, linedict, wdict)
        else:
            line += 1
            non_rec_reason = ""
            if not account.reconcile:
                non_rec_reason = (
                    " car le compte n'est pas configuré comme étant lettrable"
                )
            non_rec_msg = (
                f"Compte '{account.display_name}' non lettré sur l'OD "
                f"de TVA{non_rec_reason}. Par conséquent, Odoo ne "
                f"peut pas fournir les informations demandées pour ce compte."
            )
            linedict = {
                "date": (
                    non_rec_msg,
                    wdict["styles"]["regular_warn"],
                )
            }
            self._write_xlsx_line(sheet, line, linedict, wdict, line_warn=True)
        return line

    def _prepare_zip_deductible_vat_filename(self):
        self.ensure_one()
        return f"{self.name}-TVA_deduc_justif.zip"

    def _write_xlsx_line(self, sheet, line, linedict, wdict, line_warn=False):
        if line_warn:
            for col in wdict["coldict"].values():
                sheet.write(line, col["pos"], "", wdict["styles"]["regular_warn"])
        for key, (value, style) in linedict.items():
            sheet.write(line, wdict["coldict"][key]["pos"], value, style)

    def _prepare_xlsx_cols(self):
        cols = [  # key, label, width
            ("date", "Date Pièce", 11),
            ("move.name", "N° Pièce", 16),
            ("journal", "Journal", 12),
            ("account", "Compte", 20),
            ("debit", "Débit", 12),
            ("credit", "Crédit", 12),
            ("inv", "Lien facture", 8),
            ("supplier.name", "Fournisseur", 30),
            ("supplier.siren", "SIREN fournisseur", 12),
            ("supplier.vat", "N° TVA fournisseur", 16),
            ("inv.date", "Date facture fournisseur", 11),
            ("inv.ref", "N° facture fournisseur", 15),
            ("inv.currency", "Devise facture fournisseur", 10),
            ("inv.untaxed", "Total HT", 13),
            ("inv.total", "Total TTC", 13),
            ("inv.vat_on_payment", "TVA sur encaissement", 8),
            (
                "inv.residual",
                "Reste à payer (si TVA encaiss.)",
                13,
            ),
            ("inv.payments", "Paiements (si TVA encaiss.)", 28),
            ("inv.attach", "Facture PDF dans fichier ZIP", 20),
        ]
        coldict = {}
        pos = 0
        for key, label, width in cols:
            coldict[key] = {
                "label": label,
                "width": width,
                "pos": pos,
            }
            pos += 1
        return coldict

    def _create_xlsx_sheet(self, sheet_name, title, wdict):
        # I don't translate the content of the XLSX because DGFiP would
        # certainly not accept a document in a lang other than French anyway...
        sheet = wdict["workbook"].add_worksheet(sheet_name)
        styles = wdict["styles"]
        i = 0
        sheet.write(i, 0, title, styles["doc_title"])
        i += 2
        for vals in wdict["coldict"].values():
            sheet.write(i, vals["pos"], vals["label"], styles["col_title"])
            sheet.set_column(vals["pos"], vals["pos"], vals["width"])
        return sheet, i

    def _prepare_xlsx_styles(self, workbook):
        col_title_bg_color = "#fff9b4"
        warn_bg_color = "#ff1717"
        regular_font_size = 10
        cents = "0" * self.company_id.currency_id.decimal_places
        company_currency_num_format = (
            f"# ### ##0.{cents} {self.company_id.currency_id.symbol}"
        )
        styles = {
            "doc_title": workbook.add_format(
                {
                    "bold": True,
                    "font_size": regular_font_size + 10,
                    "font_color": "#003b6f",
                }
            ),
            "col_title": workbook.add_format(
                {
                    "bold": True,
                    "bg_color": col_title_bg_color,
                    "text_wrap": True,
                    "font_size": regular_font_size,
                    "align": "center",
                }
            ),
            "regular_date": workbook.add_format({"num_format": "dd/mm/yyyy"}),
            "regular_company_currency": workbook.add_format(
                {"num_format": company_currency_num_format}
            ),
            "regular_warn": workbook.add_format({"bg_color": warn_bg_color}),
            "regular": workbook.add_format({}),
            "regular_center": workbook.add_format({"align": "center"}),
            "regular_center_warn": workbook.add_format(
                {"bg_color": warn_bg_color, "align": "center"}
            ),
        }
        return styles

    def _create_draft_account_move(self, speedy):
        self.ensure_one()
        assert self.state in ("manual", "auto")
        if not self.line_ids.filtered(lambda x: not x.box_display_type):
            raise UserError(
                _("The declaration %s doesn't contain any line.", self.display_name)
            )
        move = speedy["am_obj"].create(self._prepare_account_move(speedy))
        return move

    def _get_box_account(self, box, raise_if_none=True, raise_if_not_unique=True):
        self.ensure_one()
        # I can't use speedy because this method is also called by onchange
        company_id = self.company_id.id
        account = box.with_company(company_id).account_id or False
        if account:
            return account
        if not box.account_code:
            if raise_if_none:
                raise UserError(
                    _(
                        "On box '%s', the Account Code is not set. "
                        "You may want to setup a specific account on that box.",
                        box.display_name,
                    )
                )
            return None
        accounts = self.env["account.account"].search(
            [
                ("company_id", "=", company_id),
                ("deprecated", "=", False),
                ("code", "=like", box.account_code + "%"),
            ]
        )
        if not accounts:
            if raise_if_none:
                raise UserError(
                    _(
                        "Box '%(box)s' is configured with Manual Account Code "
                        "'%(account_code)s', but there are no accounts that start "
                        "with this code in company '%(company)s'. You may want to "
                        "setup a specific account on that box.",
                        box=box.display_name,
                        account_code=box.account_code,
                        company=self.company_id.display_name,
                    )
                )
            return None
        if len(accounts) > 1:
            logger.warning(
                "There are %d accounts that start with '%s' in company %s",
                len(accounts),
                box.account_code,
                self.company_id.display_name,
            )
            if raise_if_not_unique:
                raise UserError(
                    _(
                        "There are %(account_count)s accounts whose code start with "
                        "%(account_prefix)s in company '%(company)s' : %(account_list)s. "
                        "Odoo expects to have only one.",
                        account_count=len(accounts),
                        account_prefix=box.account_code,
                        company=self.company_id.display_name,
                        account_list=", ".join([a.code for a in accounts]),
                    )
                )
        return accounts[0]

    def unlink(self):
        for rec in self:
            if rec.state != "manual":
                raise UserError(
                    _(
                        "Cannot delete VAT return '%s' because it is not in "
                        "'Manual Lines' state.",
                        rec.display_name,
                    )
                )
        return super().unlink()

    def print_ca3(self):
        self.ensure_one()
        # In manu/auto, we re-generate it every time because comment_dgfip
        # may have changed
        if self.ca3_attachment_id and self.state in ("manual", "auto"):
            self.ca3_attachment_id.unlink()
        if not self.ca3_attachment_id:
            self.generate_ca3_attachment()
        action = {
            "name": "CA3",
            "type": "ir.actions.act_url",
            "url": f"web/content/?model={self._name}&id={self.id}&"
            f"filename_field=ca3_attachment_name&field=ca3_attachment_datas&"
            f"download=true&filename={self.ca3_attachment_name}",
            "target": "new",
            # target: "new" and NOT "self", otherwise you get the following bug:
            # after this action, all UserError won't show a pop-up to the user
            # but will only show a warning message in the logs until the web
            # page is reloaded
        }
        return action

    def generate_ca3_attachment(self):
        ca3_page_total = 3
        fontsizes_per_page = [10, 8, 8]
        packets = [io.BytesIO() for x in range(ca3_page_total)]
        # create a new PDF that contains the additional text with Reportlab
        page2canvas = {}
        for page_nr in range(ca3_page_total):
            page2canvas[page_nr] = canvas.Canvas(packets[page_nr], pagesize=A4)
            page2canvas[page_nr].setFont("Helvetica", fontsizes_per_page[page_nr])

        for line in self.line_ids.filtered(
            lambda x: not x.box_display_type and not x.box_form_code == "3310A"
        ):
            box = line.box_id
            if not box.print_page or not box.print_x or not box.print_y:
                logger.warning(
                    "Box %s not printed on PDF because missing page or x/y position",
                    box.name,
                )
                continue
            if box.edi_type == "MOA":
                pdf_value = format(line.value, "_").replace("_", chr(160))
            elif box.edi_type == "CCI_TBX":
                pdf_value = line.value_bool and "x" or False
            else:
                raise UserError(_("EDI type not supported for box '%s'.", box.name))

            if pdf_value:
                page2canvas[int(box.print_page) - 1].drawRightString(
                    box.print_x, box.print_y, pdf_value
                )
        # Add static prints
        static_prints = {
            "company_name": {
                "value": self.company_id.name,
                "x": 282,
                "y": 656,
            },
            "siret": {
                "value": self.company_id.siret,
                "x": 408,
                "y": 524,
            },
            "vat": {
                "value": self.company_id.vat,
                "x": 408,
                "y": 509,
            },
            "start_day": {
                "value": "%02d" % self.start_date.day,
                "x": 151,
                "y": 741,
            },
            "start_month": {
                "value": "%02d" % self.start_date.month,
                "x": 169,
                "y": 741,
            },
            "start_year": {
                "value": str(self.start_date.year),
                "x": 186,
                "y": 741,
            },
            "end_day": {
                "value": "%02d" % self.end_date.day,
                "x": 220,
                "y": 741,
            },
            "end_month": {
                "value": "%02d" % self.end_date.month,
                "x": 239,
                "y": 741,
            },
            "end_year": {
                "value": str(self.end_date.year),
                "x": 258,
                "y": 741,
            },
        }
        for pvals in static_prints.values():
            if pvals["value"]:
                page2canvas[0].drawString(pvals["x"], pvals["y"], pvals["value"])
        # Comment => block of text
        if self.comment_dgfip:
            text_object = page2canvas[0].beginText(21, 250)
            for line in self.comment_dgfip.splitlines():
                line_wrapped = textwrap.wrap(
                    line, width=120, break_long_words=False, replace_whitespace=False
                )
                for wline in line_wrapped:
                    text_object.textLine(wline.rstrip())
            page2canvas[0].drawText(text_object)
        # Address => use flowable because it is multiline
        addr = self.company_id.partner_id._display_address(without_company=True)
        if addr:
            styleSheet = getSampleStyleSheet()
            style = styleSheet["BodyText"]
            style.fontSize = 8
            style.leading = 9
            addr_para = Paragraph(addr.replace("\n", "<br/>"), style)
            addr_para.wrap(570 - 282, 636 - 602)
            addr_para.drawOn(page2canvas[0], 282, 602)
        for canv in page2canvas.values():
            canv.save()

        # move to the beginning of the StringIO buffer
        watermark_pdf_list = []
        for page_nr in range(ca3_page_total):
            packets[page_nr].seek(0)
            watermark_pdf_list.append(PdfReader(packets[page_nr]))
        # read your existing PDF
        with tools.file_open(
            "l10n_fr_account_vat_return/report/CA3_cerfa.pdf", "rb"
        ) as ca3_original_fd:
            ca3_writer = PdfWriter(ca3_original_fd)
            # add the "watermark" (which is the new pdf) on the existing page
            for page_nr in range(ca3_page_total):
                ca3_writer.pages[page_nr].merge_page(
                    watermark_pdf_list[page_nr].pages[0]
                )
                ca3_writer.pages[page_nr].compress_content_streams()
            # finally, write "output" to a real file
            out_ca3_io = io.BytesIO()
            ca3_writer.write(out_ca3_io)
            out_ca3_bytes = out_ca3_io.getvalue()

        filename = f"CA3_{self.name}.pdf"
        attach = self.env["ir.attachment"].create(
            {
                "name": filename,
                "res_id": self.id,
                "res_model": self._name,
                "raw": out_ca3_bytes,
            }
        )
        self.write({"ca3_attachment_id": attach.id})


class L10nFrAccountVatReturnLine(models.Model):
    _name = "l10n.fr.account.vat.return.line"
    _description = "VAT Return Line for France (CA3 line)"
    _order = "parent_id, box_sequence"
    _check_company_auto = True

    parent_id = fields.Many2one(
        "l10n.fr.account.vat.return", string="VAT Return", ondelete="cascade"
    )
    company_id = fields.Many2one(related="parent_id.company_id", store=True)
    state = fields.Selection(related="parent_id.state", store=True)
    box_id = fields.Many2one(
        "l10n.fr.account.vat.box", string="Box", ondelete="restrict", required=True
    )
    box_code = fields.Char(related="box_id.code", store=True)
    box_form_code = fields.Selection(related="box_id.form_code", store=True)
    box_edi_type = fields.Selection(related="box_id.edi_type", store=True)
    box_edi_code = fields.Char(related="box_id.edi_code", store=True)
    box_accounting_method = fields.Selection(
        related="box_id.accounting_method", store=True
    )
    box_push_box_id = fields.Many2one(related="box_id.push_box_id", store=True)
    box_push_sequence = fields.Integer(related="box_id.push_sequence", store=True)
    box_meaning_id = fields.Char(related="box_id.meaning_id", store=True)
    box_manual = fields.Boolean(related="box_id.manual", store=True)
    box_name = fields.Char(related="box_id.name", store=True)
    box_display_type = fields.Selection(related="box_id.display_type", store=True)
    box_sequence = fields.Integer(related="box_id.sequence", store=True)
    box_negative = fields.Boolean(related="box_id.negative", store=True)
    value = fields.Integer(
        compute="_compute_value", store=True
    )  # MOA, QTY, PCD, CCI_TBX (manual + auto)
    value_float = fields.Float(
        compute="_compute_value", store=True, string="Value Before Rounding"
    )  # MOA, QTY, PCD (auto)
    value_bool = fields.Boolean(string="Value (Y/N)")  # CCI_TBX (manual + auto)
    value_manual_int = fields.Integer(string="Integer Value")  # MOA, QTY, PCD (manual)
    value_char = fields.Char(
        string="Text"
    )  # FTX, NAD (manual + auto), except for BA field
    log_ids = fields.One2many(
        "l10n.fr.account.vat.return.line.log",
        "parent_id",
        string="Computation Details",
        readonly=True,
    )
    manual_account_id = fields.Many2one(
        "account.account",
        string="Account",
        compute="_compute_manual_account_id",
        check_company=True,
        readonly=False,
        store=True,
        precompute=True,
        domain="[('company_id', '=', company_id), ('deprecated', '=', False)]",
    )
    manual_analytic_distribution = fields.Json(
        string="Analytic",
        compute="_compute_manual_account_id",
        readonly=False,
        store=True,
        precompute=True,
    )
    analytic_precision = fields.Integer(
        default=lambda self: self.env["decimal.precision"].precision_get(
            "Percentage Analytic"
        ),
    )

    # idea: field value_tree type fields.Char() that would agregate
    # all types (adding € sign for MOA) and be used in tree view
    # but the content would be aligned on the right => not so good idea...

    _sql_constraints = [
        ("unique_return_box", "unique(parent_id, box_id)", "This line already exists!")
    ]

    @api.depends("box_id")
    def _compute_manual_account_id(self):
        aadmo = self.env["account.analytic.distribution.model"]
        for line in self:
            manual_account_id = False
            manual_analytic_distribution = False
            if line.box_id and line.box_id.manual and line.parent_id:
                account = line.parent_id._get_box_account(
                    line.box_id, raise_if_none=False, raise_if_not_unique=False
                )
                if account:
                    manual_account_id = account.id
                    manual_analytic_distribution = aadmo._get_distribution(
                        {
                            "account_prefix": account.code,
                            "company_id": line.parent_id.company_id.id,
                        }
                    )
            line.manual_account_id = manual_account_id
            line.manual_analytic_distribution = manual_analytic_distribution

    @api.constrains("value_manual_int")
    def _check_values(self):
        for line in self:
            if line.value_manual_int < 0:
                raise UserError(
                    _(
                        "The value of line '%(box)s' (%(value)d) is negative.",
                        box=line.box_id.display_name,
                        value=line.value_manual_int,
                    )
                )
            if line.box_id.edi_type == "PCD" and line.value_manual_int > 100:
                raise UserError(
                    _(
                        "The value of line '%(box)s' (%(value)d) is over 100.",
                        box=line.box_id.display_name,
                        value=line.value_manual_int,
                    )
                )

    @api.depends(
        "log_ids",
        "log_ids.amount",
        "value_bool",
        "value_manual_int",
        "box_id",
        "box_id.negative",
    )
    def _compute_value(self):
        rg_res = self.env["l10n.fr.account.vat.return.line.log"].read_group(
            [("parent_id", "in", self.ids)], ["parent_id", "amount"], ["parent_id"]
        )
        mapped_data = {x["parent_id"][0]: x["amount"] for x in rg_res}
        for line in self:
            value = 0
            value_float = 0
            sign = line.box_id.negative and -1 or 1
            if not line.box_id.display_type:
                if line.box_id.edi_type in ("MOA", "QTY", "PCD"):
                    if line.box_id.manual:
                        value = line.value_manual_int
                    else:
                        value_float = mapped_data.get(line.id, 0)
                        # Python 3.10.12
                        # >>> round(40147.5)
                        # 40148
                        # >>> round(40146.5)
                        # 40146
                        # it's why I used odoo's float_round
                        # which doesn't have this problem
                        value = int(float_round(value_float, precision_digits=0))
                elif line.box_id.edi_type == "CCI_TBX":
                    value = int(line.value_bool)
            line.value = value * sign
            line.value_float = value_float * sign


class L10nFrAccountVatReturnLineLog(models.Model):
    _name = "l10n.fr.account.vat.return.line.log"
    _description = "Compute log of VAT Return Line for France"
    _order = "parent_id, id"

    # for MOA fields only
    parent_id = fields.Many2one(
        "l10n.fr.account.vat.return.line",
        string="VAT Return Line",
        ondelete="cascade",
        readonly=True,
    )
    parent_parent_id = fields.Many2one(related="parent_id.parent_id", store=True)
    # account_id is used for the generation of the account.move
    # when box_accounting_method != False, and it is just informative
    # when box_accounting_method = False
    account_id = fields.Many2one(
        "account.account", string="Account", ondelete="restrict", readonly=True
    )
    # I don't inherit from analytic.mixin because I don't want analytic_distribution
    # to have a compute method
    analytic_distribution = fields.Json(
        string="Analytic",
        readonly=True,
    )
    analytic_precision = fields.Integer(
        default=lambda self: self.env["decimal.precision"].precision_get(
            "Percentage Analytic"
        ),
    )
    compute_type = fields.Selection(
        [
            # previously used for untaxed operations (until 01/2024). I keep it for the
            # the old log lines
            ("period_balance", "Period Balance"),
            # used for untaxed operations, starting 02/2024
            ("period_balance_sale", "Period Balance in Sale Journal"),
            ("balance", "Ending Balance"),  # used for VAT boxes
            ("balance_ratio", "Ending Balance x Ratio"),  # used for VAT boxes
            ("unpaid_vat_on_payment", "Unpaid VAT on Payment"),  # used for VAT boxes
            (
                "base_from_balance",
                "Base from Ending Balance",
            ),  # used for taxed operations
            (
                "base_from_balance_ratio",
                "Base from Ending Balance x Ratio",
            ),  # used for taxed operations
            (
                "base_from_unpaid_vat_on_payment",
                "Base from Unpaid VAT on Payment",
            ),  # used for taxed operations
            ("computed_vat_amount", "Computed VAT Amount"),  # for Monaco
            ("rate", "VAT Amount / VAT Rate"),
            ("box", "Box Value"),  # used for sum boxes (totals)
            ("manual", "Manual"),  # used for credit VAT reimbursement line
            # used to comply with stupid consistency controls that don't tolerate
            # few € difference caused by rounding
            ("adjustment", "Adjustment"),
        ],
        required=True,
        readonly=True,
    )
    amount = fields.Float(readonly=True)
    origin_move_id = fields.Many2one(
        "account.move", string="Source Invoice", readonly=True
    )
    note = fields.Char()

    @api.constrains("parent_id", "account_id", "compute_type")
    def _check_log_line(self):
        for log in self:
            if log.parent_id and log.parent_id.box_accounting_method:
                if not log.account_id:
                    raise ValidationError(
                        _(
                            "Error in the generation of the computation and "
                            "accounting details of box '%s': this box has an "
                            "accounting method but the account is not set.",
                            log.parent_id.box_id.display_name,
                        )
                    )
                if log.compute_type == "adjustment":
                    raise ValidationError(
                        _(
                            "Error in the generation of box '%s': "
                            "it has an accounting method, so it cannot have "
                            "any adjustment line.",
                            log.parent_id.box_id.display_name,
                        )
                    )


class L10nFrAccountVatReturnAutoliqLine(models.Model):
    _name = "l10n.fr.account.vat.return.autoliq.line"
    _description = "VAT Return Autoliq Line for France"
    _order = "parent_id, id"
    _check_company_auto = True

    parent_id = fields.Many2one(
        "l10n.fr.account.vat.return", string="VAT Return", ondelete="cascade"
    )
    company_id = fields.Many2one(related="parent_id.company_id", store=True)
    # no required=True, to avoid error if move line is deleted
    move_line_id = fields.Many2one(
        "account.move.line", string="Journal Item", check_company=True
    )
    move_id = fields.Many2one(
        related="move_line_id.move_id", string="Journal Entry", store=True
    )
    journal_id = fields.Many2one(related="move_id.journal_id", store=True)
    date = fields.Date(related="move_id.date", store=True)
    partner_id = fields.Many2one(related="move_line_id.partner_id", store=True)
    account_id = fields.Many2one(related="move_line_id.account_id", store=True)
    ref = fields.Char(related="move_id.ref", store=True)
    label = fields.Char(related="move_line_id.name", store=True)
    company_currency_id = fields.Many2one(
        related="move_line_id.company_currency_id", store=True
    )
    debit = fields.Monetary(
        related="move_line_id.debit", currency_field="company_currency_id", store=True
    )
    credit = fields.Monetary(
        related="move_line_id.credit", currency_field="company_currency_id", store=True
    )
    product_ratio = fields.Float(digits=(16, 2))
    autoliq_type = fields.Selection(
        [
            ("intracom", "Intracom"),
            ("extracom", "Extracom"),
        ],
        required=True,
        string="Type",
    )
    compute_type = fields.Selection(
        [
            ("auto", "Auto"),
            ("manual", "Manual"),
        ],
        required=True,
    )
    vat_rate_int = fields.Integer(
        string="VAT Rate", required=True, help="VAT rate x 100"
    )

    @api.constrains("product_ratio")
    def _check_autoliq_line(self):
        for line in self:
            if (
                float_compare(line.product_ratio, 0, precision_digits=2) < 0
                or float_compare(line.product_ratio, 100, precision_digits=2) > 0
            ):
                raise ValidationError(
                    _(
                        "On journal item '%(move_line)s', the product ratio must be "
                        "between 0%% and 100%% (current value: %(ratio)s %%).",
                        move_line=line.move_line_id.display_name,
                        ratio=line.product_ratio,
                    )
                )


class L10nFrAccountVatReturnUnpaidVatOnPaymentManualLine(models.Model):
    _name = "l10n.fr.account.vat.return.unpaid.vat.on.payment.manual.line"
    _description = "VAT Return Unpaid VAT On Payment Manual Line"
    _order = "parent_id, id"
    _check_company_auto = True

    parent_id = fields.Many2one(
        "l10n.fr.account.vat.return", string="VAT Return", ondelete="cascade"
    )
    company_id = fields.Many2one(related="parent_id.company_id", store=True)
    company_currency_id = fields.Many2one(
        related="parent_id.company_id.currency_id", store=True
    )
    account_id = fields.Many2one(
        "account.account",
        string="VAT Account",
        required=True,
        domain="[('id', 'in', parent.unpaid_vat_on_payment_manual_line_filter_account_ids)]",
    )
    amount = fields.Monetary(
        string="VAT Amount",
        currency_field="company_currency_id",
        required=True,
        help="Enter the unpaid VAT on payment amount that Odoo cannot compute "
        "automatically because it is not linked to an invoice in Odoo (but "
        "related to the starting balance for example). "
        "This feature is useful in the first months of use of Odoo accounting, "
        "when there are unpaid VAT on payment invoices in the previous "
        "fiscal year and the accounting of the previous fiscal year was not "
        "handled in Odoo.",
    )
    note = fields.Char()

    _sql_constraints = [
        (
            "parent_account_uniq",
            "unique(parent_id, account_id)",
            "This manual unpaid VAT on payment line already exists.",
        )
    ]
