# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import io
import json
import logging
import textwrap
import uuid
from collections import defaultdict

from dateutil.relativedelta import relativedelta
from PyPDF2 import PdfFileReader, PdfFileWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils, float_is_zero
from odoo.tools.misc import format_amount, format_date

from .l10n_fr_account_vat_box import PUSH_RATE_PRECISION

logger = logging.getLogger(__name__)

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
    )
    end_date = fields.Date(compute="_compute_name_end_date", store=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
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
        string="State",
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
        "_reimbursement_type_selection", string="Reimbursement Type", readonly=True
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
        string="Reimbursement Comment for DGFIP",
        states={"sent": [("readonly", True)], "posted": [("readonly", True)]},
    )
    selenium_attachment_id = fields.Many2one("ir.attachment")
    selenium_attachment_datas = fields.Binary(
        related="selenium_attachment_id.datas", string="Selenium File"
    )
    selenium_attachment_name = fields.Char(
        related="selenium_attachment_id.name", string="Selenium Filename"
    )
    ca3_attachment_id = fields.Many2one("ir.attachment", string="CA3 Attachment")
    ca3_attachment_datas = fields.Binary(
        related="ca3_attachment_id.datas", string="CA3 File"
    )
    ca3_attachment_name = fields.Char(
        related="ca3_attachment_id.name", string="CA3 Filename"
    )
    comment_dgfip = fields.Text(
        string="Comment for DGFIP",
        states={"sent": [("readonly", True)], "posted": [("readonly", True)]},
    )
    line_ids = fields.One2many(
        "l10n.fr.account.vat.return.line",
        "parent_id",
        string="Return Lines",
        readonly=True,
        states={"manual": [("readonly", False)]},
    )

    _sql_constraints = [
        (
            "start_company_uniq",
            "unique(start_date, company_id)",
            "A VAT return with the same start date already exists in this company!",
        )
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

    @api.constrains("start_date", "vat_periodicity")
    def _check_start_date(self):
        for rec in self:
            if rec.start_date.day != 1:
                raise ValidationError(
                    _("The start date (%s) must be the first day of the month.")
                    % format_date(self.env, rec.start_date)
                )
            if rec.vat_periodicity == "3" and rec.start_date.month not in MONTH2QUARTER:
                raise ValidationError(
                    _("The start date (%s) must be the first day of a quarter.")
                    % format_date(self.env, rec.start_date)
                )

    @api.constrains("comment_dgfip", "reimbursement_comment_dgfip")
    def _check_comment_dgfip(self):
        max_comment = 5 * 512
        comment_fields = {
            "comment_dgfip": _("Comment for DGFIP"),
            "reimbursement_comment_dgfip": _("Reimbursement Comment for DGFIP"),
        }
        for rec in self:
            for field_name, field_label in comment_fields.items():
                if rec[field_name] and len(rec[field_name]) > max_comment:
                    raise ValidationError(
                        _(
                            "The field '%s' is too long: it has %d caracters "
                            "whereas the maximum is %d caracters."
                        )
                        % (field_label, len(rec[field_name]), max_comment)
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
                    name = "%s-T%s" % (
                        start_date.year,
                        MONTH2QUARTER.get(start_date.month, "error"),
                    )
                elif rec.vat_periodicity == "12":
                    if start_date.month == 1:
                        name = str(start_date.year)
                    else:
                        name = "%s-%s" % (start_date.year, end_date.year)
                if end_date.month == 12 or rec.vat_periodicity == "12":
                    reimbursement_min_amount = MINIMUM_END_YEAR_AMOUNT
            rec.name = name
            rec.end_date = end_date
            rec.reimbursement_min_amount = reimbursement_min_amount

    @api.depends(
        "reimbursement_min_amount", "vat_credit_total", "state", "reimbursement_type"
    )
    def _compute_reimbursement_show_button(self):
        for rec in self:
            reimbursement_show_button = False
            if (
                rec.state == "auto"
                and rec.vat_credit_total
                and rec.vat_credit_total > rec.reimbursement_min_amount
                and not rec.reimbursement_type
            ):
                reimbursement_show_button = True
            rec.reimbursement_show_button = reimbursement_show_button

    @api.onchange("company_id")
    def company_id_change(self):
        if self.company_id and self.company_id.fr_vat_periodicity:
            self.vat_periodicity = self.company_id.fr_vat_periodicity
            self.bank_account_id = self.company_id.fr_vat_bank_account_id.id or False
            last_return = self.search(
                [("company_id", "=", self.company_id.id)],
                limit=1,
                order="start_date desc",
            )
            if last_return:
                self.start_date = last_return.end_date + relativedelta(days=1)
            else:
                today = fields.Date.context_today(self)
                if self.vat_periodicity == "1":
                    self.start_date = today + relativedelta(months=-1, day=1)
                elif self.vat_periodicity == "3":
                    start_date = today + relativedelta(months=-3, day=1)
                    while start_date.month not in MONTH2QUARTER:
                        start_date -= relativedelta(months=1)
                    self.start_date = start_date
                elif self.vat_periodicity == "12":
                    fy_date_from, fy_date_to = date_utils.get_fiscal_year(
                        today + relativedelta(years=-1),
                        day=self.company_id.fiscalyear_last_day,
                        month=int(self.company_id.fiscalyear_last_month),
                    )
                    self.start_date = fy_date_from

    def _prepare_speedy(self):
        # Generate a speed-dict called speedy that is used in several methods
        self.ensure_one()
        company_domain = [("company_id", "=", self.company_id.id)]
        base_domain = company_domain + [("parent_state", "=", "posted")]
        base_domain_period = base_domain + [
            ("date", ">=", self.start_date),
            ("date", "<=", self.end_date),
        ]
        base_domain_end = base_domain + [("date", "<=", self.end_date)]
        base_domain_end_previous = base_domain + [("date", "<", self.start_date)]
        movetype2label = dict(
            self.env["account.move"].fields_get("move_type", "selection")["move_type"][
                "selection"
            ]
        )
        speedy = {
            "company_id": self.company_id.id,
            "currency": self.company_id.currency_id,
            "company_domain": company_domain,
            "base_domain_period": base_domain_period,
            "base_domain_end": base_domain_end,
            "base_domain_end_previous": base_domain_end_previous,
            "end_date_formatted": format_date(self.env, self.end_date),
            "start_date_formatted": format_date(self.env, self.start_date),
            "movetype2label": movetype2label,
            "line_obj": self.env["l10n.fr.account.vat.return.line"],
            "log_obj": self.env["l10n.fr.account.vat.return.line.log"],
            "box_obj": self.env["l10n.fr.account.vat.box"],
            "aa_obj": self.env["account.account"],
            "am_obj": self.env["account.move"],
            "aml_obj": self.env["account.move.line"],
            "aj_obj": self.env["account.journal"],
            "afp_obj": self.env["account.fiscal.position"],
            "afpt_obj": self.env["account.fiscal.position.tax"],
            "afpa_obj": self.env["account.fiscal.position.account"],
            "at_obj": self.env["account.tax"],
        }
        speedy["bank_cash_journals"] = speedy["aj_obj"].search(
            speedy["company_domain"] + [("type", "in", ("bank", "cash"))]
        )
        return speedy

    def _get_adjust_accounts(self, speedy):
        # This is the method to inherit if you want to select the appropriate
        # accounts via a configuration parameter
        # To avoid to have too many configuration params,
        # considering that this module is only for France and
        # that all French companies must use the PCG,
        # I select the account based on the code they should have
        self.ensure_one()
        account_lookup = {
            "expense_adjust_account": ("658", "Charges diverses de gestion courante"),
            "income_adjust_account": ("758", "Produits divers de gestion courante"),
        }
        for key, (account_code, account_name) in account_lookup.items():
            limit = not account_code.startswith("445") and 1 or None
            account = speedy["aa_obj"].search(
                speedy["company_domain"] + [("code", "=like", account_code + "%")],
                limit=limit,
            )
            if not account:
                raise UserError(
                    _(
                        "There is no account %s %s in the chart of account "
                        "of company '%s'."
                    )
                    % (account_code, account_name, self.company_id.display_name)
                )
            if len(account) > 1:
                raise UserError(
                    _(
                        "There are %d accounts %s %s in the chart of account "
                        "of company '%s'. This scenario is not supported."
                    )
                    % (
                        len(account),
                        account_code,
                        account_name,
                        self.company_id.display_name,
                    )
                )
            speedy[key] = account

    def manual2auto(self):
        self.ensure_one()
        assert self.state == "manual"
        speedy = self._prepare_speedy()
        self._setup_data_pre_check(speedy)
        self._delete_move_and_attachments()  # should not be necessary at that step
        self._generate_operation_untaxed(speedy)
        self._generate_due_vat(speedy)
        self._generate_deductible_vat(speedy)
        self._switch_negative_boxes(speedy)
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
        # del auto lines
        self.line_ids.filtered(lambda x: x.box_box_type != "manual").unlink()
        self._delete_move_and_attachments()
        vals = {"state": "manual"}
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
                        "cannot be deleted because it is already posted."
                    )
                    % self.move_id.display_name
                )
            self.move_id.unlink()
        if self.ca3_attachment_id:
            self.ca3_attachment_id.unlink()
        if self.selenium_attachment_id:
            self.selenium_attachment_id.unlink()

    def auto2sent(self):
        self.ensure_one()
        assert self.state == "auto"
        if not self.ca3_attachment_id:  # for archive
            self.generate_ca3_attachment()
        self.write(
            {
                "state": "sent",
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
        self._reconcile_account_move(move, speedy)
        if (
            self.company_id.fr_vat_update_lock_dates
            and self.company_id.period_lock_date < self.end_date
        ):
            self.sudo().company_id.write({"period_lock_date": self.end_date})
        self.write({"state": "posted"})

    def _setup_data_pre_check(self, speedy):
        self.ensure_one()
        # Block if there are unposted moves before end_date
        unposted_move_count = speedy["am_obj"].search_count(
            [("date", "<=", self.end_date), ("state", "!=", "posted")]
            + speedy["company_domain"]
        )
        if unposted_move_count:
            raise UserError(
                _(
                    "There is/are %d unposted journal entry/entries dated before %s. "
                    "You should post this/these journal entry/entries or "
                    "delete it/them."
                )
                % (unposted_move_count, format_date(self.env, self.end_date))
            )
        bad_fp = speedy["afp_obj"].search(
            speedy["company_domain"] + [("fr_vat_type", "=", False)], limit=1
        )
        if bad_fp:
            raise UserError(
                _(
                    "Type not set on fiscal position '%s'. It must be set on all "
                    "fiscal positions."
                )
                % bad_fp.display_name
            )
        on_payment_taxes_count = speedy["at_obj"].search_count(
            speedy["company_domain"] + [("tax_exigibility", "=", "on_payment")]
        )
        if on_payment_taxes_count:
            raise UserError(
                _(
                    "There are still On Payment taxes in company '%s'. "
                    "To handle on payment VAT, this module uses a different "
                    "implementation than the native solution based on a "
                    "configuration parameter on taxes."
                )
                % self.company_id.display_name
            )

    def _generate_ca3_bottom_totals(self, speedy):
        # Process the END of CA3 by hand
        # Delete no_push_total and end_total lines
        # it corresponds to the 4 sum boxes at the bottom block of CA3
        lines_to_del = speedy["line_obj"].search(
            [
                ("parent_id", "=", self.id),
                (
                    "box_box_type",
                    "in",
                    (
                        "no_push_total_debit",
                        "no_push_total_credit",
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
        due_vat_total_box = speedy["box_obj"]._box_from_single_box_type("due_vat_total")
        vat_to_pay_line = speedy["line_obj"].search(
            [("parent_id", "=", self.id), ("box_id", "=", due_vat_total_box.id)]
        )
        vat_to_pay = vat_to_pay_line and vat_to_pay_line.value or 0

        deduc_vat_total_box = speedy["box_obj"]._box_from_single_box_type(
            "deductible_vat_total"
        )
        vat_deduc_line = speedy["line_obj"].search(
            [("parent_id", "=", self.id), ("box_id", "=", deduc_vat_total_box.id)]
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
        if sub_total > 0:
            box = speedy["box_obj"]._box_from_single_box_type("no_push_total_debit")
        else:
            box = speedy["box_obj"]._box_from_single_box_type("no_push_total_credit")
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
                "log_ids": [(0, 0, x) for x in logs],
            }
        )
        # Generate push lines for the very bottom of CA3
        self._create_push_lines("end", speedy)

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
                if float_is_zero(
                    to_push_line.box_id.push_rate, precision_digits=PUSH_RATE_PRECISION
                ):
                    # simple sum boxes
                    amount = cur_amounts[to_push_line.box_id.id]
                    note = _("%s (add)") % to_push_line.box_id.display_name
                else:
                    # rate push boxes that can be found in 3310A
                    amount = int(
                        round(
                            to_push_line.box_id.push_rate
                            * cur_amounts[to_push_line.box_id.id]
                            / 100
                        )
                    )
                    note = "%s %% x %s €, %s" % (
                        to_push_line.box_id.push_rate,
                        cur_amounts[to_push_line.box_id.id],
                        to_push_line.box_id.display_name,
                    )
                push_box = to_push_line.box_id.push_box_id
                # prepare new log line
                account_id = False
                if push_box.accounting_method:
                    account_id = self._get_box_account(push_box).id

                new_log_lines[push_box].append(
                    (
                        0,
                        0,
                        {
                            "compute_type": "box",
                            "note": note,
                            "amount": amount,
                            "account_id": account_id,
                            "analytic_account_id": push_box.analytic_account_id.id
                            or False,
                        },
                    )
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
        box = speedy["box_obj"]._box_from_single_box_type("credit_deferment")
        account = self._get_box_account(box)
        balance = account._fr_vat_get_balance("base_domain_end", speedy)
        # Check that the balance of 445670 is an integer
        if speedy["currency"].compare_amounts(balance, int(balance)):
            raise UserError(
                _(
                    "The balance of account '%s' is %s. "
                    "In France, it should be a integer amount."
                )
                % (
                    account.display_name,
                    format_amount(self.env, balance, speedy["currency"]),
                )
            )
        # Check that the balance of 445670 is the right sign
        compare_bal = speedy["currency"].compare_amounts(balance, 0)
        if compare_bal < 0:
            raise UserError(
                _("The balance of account '%s' is %s. It should always be positive.")
                % (
                    account.display_name,
                    format_amount(self.env, balance, speedy["currency"]),
                )
            )
        elif compare_bal > 0:
            speedy["line_obj"].create(
                {
                    "parent_id": self.id,
                    "box_id": box.id,
                    "log_ids": [
                        (
                            0,
                            0,
                            {
                                "account_id": account.id,
                                "compute_type": "balance",
                                "amount": balance,
                            },
                        )
                    ],
                }
            )

    def _generate_due_vat(self, speedy):
        self.ensure_one()
        # TODO Check that an account can't be used in both autoliq and non-autoliq?
        # COMPUTE LINES
        # There are 2 important dicts:
        # 1. rate2logs: generate block "B décompte de la TVA à payer"
        # both columns "taxe due" and "Base hors taxe"
        rate2logs = defaultdict(list)
        # 2. taxedop_type2logs: generate block top left "Opérations imposables"
        taxedop_type2logs = defaultdict(list)

        # Compute France and Monaco
        monaco_logs = self._generate_due_vat_france(
            speedy, rate2logs, taxedop_type2logs
        )
        # Compute Auto-liquidation
        autoliq_intracom_product_logs = self._generate_due_vat_autoliq(
            speedy, rate2logs, taxedop_type2logs
        )

        # CREATE LINES
        # Boxes 08, 09, 9A
        self._generate_due_vat_create_vat_to_pay_lines(speedy, rate2logs)
        # Boxes for taxed operations: A1, B3, A3, B2
        for taxedop_type, logs in taxedop_type2logs.items():
            box_type = "taxed_op_%s" % taxedop_type
            self._create_line(speedy, logs, box_type)
        # Box 17 "dont TVA sur acquisitions intracom"
        self._create_line(
            speedy, autoliq_intracom_product_logs, "due_vat_intracom_product"
        )
        # Box 18 Dont TVA sur opérations à destination de Monaco
        self._create_line(speedy, monaco_logs, "due_vat_monaco")

    def _generate_due_vat_prepare_sale_struct(self, speedy):
        # REGULAR SALE TAXES
        sale_vat_account2rate = {}
        sale_vat_accounts = speedy["aa_obj"]
        regular_due_vat_taxes = speedy["at_obj"].search(
            speedy["company_domain"]
            + [
                ("amount_type", "=", "percent"),
                ("amount", ">", 0),
                ("fr_vat_autoliquidation", "=", False),
                ("type_tax_use", "=", "sale"),
            ]
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
                        "invoices configured with an account and with '100%% of tax'."
                    )
                    % tax.display_name
                )
            sale_vat_account = invoice_lines.account_id
            refund_lines = tax.refund_repartition_line_ids.filtered(
                lambda x: x.repartition_type == "tax"
                and x.account_id
                and int(x.factor_percent) == 100
            )
            if len(refund_lines) != 1:
                raise UserError(
                    _(
                        "Tax '%s' should have only one distribution line for "
                        "credit notes configured with an account and with '100%% of tax'."
                    )
                    % tax.display_name
                )
            refund_vat_account = refund_lines.account_id
            if refund_vat_account != sale_vat_account:
                raise UserError(
                    _(
                        "Tax '%s' has an account for invoice (%s) which is "
                        "different from the account for refund (%s). "
                        "This scenario not supported."
                    )
                    % (
                        tax.display_name,
                        sale_vat_account.display_name,
                        refund_vat_account.display_name,
                    )
                )
            rate_int = int(tax.amount * 100)
            if (
                sale_vat_account in sale_vat_account2rate
                and sale_vat_account2rate[sale_vat_account] != rate_int
            ):
                raise UserError(
                    _(
                        "Account '%s' is used on several sale VAT taxes "
                        "for different rates (%.2f%% and %.2f%%)."
                    )
                    % (
                        sale_vat_account.display_name,
                        rate_int / 100,
                        sale_vat_account2rate[sale_vat_account] / 100,
                    )
                )
            sale_vat_account2rate[sale_vat_account] = rate_int
            sale_vat_accounts |= sale_vat_account

        assert sale_vat_accounts
        return sale_vat_accounts, sale_vat_account2rate

    def _generate_due_vat_france(self, speedy, rate2logs, taxedop_type2logs):
        (
            sale_vat_accounts,
            sale_vat_account2rate,
        ) = self._generate_due_vat_prepare_sale_struct(speedy)
        logger.debug("sale_vat_account2rate=%s", sale_vat_account2rate)
        vat_on_payment_account2logs = self._vat_on_payment(
            "out", sale_vat_accounts.ids, speedy
        )
        # generate taxedop_type2logs['france'] and rate2logs
        for sale_vat_account, rate_int in sale_vat_account2rate.items():
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
                rate2logs[rate_int].append(
                    {
                        "account_id": sale_vat_account.id,
                        "compute_type": "balance",
                        "amount": balance,
                    }
                )
                base = balance * 10000 / rate_int
                taxedop_type2logs["france"].append(
                    {
                        "account_id": sale_vat_account.id,
                        "compute_type": "balance",
                        "amount": base,
                        "note": _("VAT amount %s, Rate %.2f%%, Base %s")
                        % (
                            format_amount(self.env, balance, speedy["currency"]),
                            rate_int / 100,
                            format_amount(self.env, base, speedy["currency"]),
                        ),
                    }
                )
            # remove on_payment invoices unpaid on end_date for rate2logs
            rate2logs[rate_int] += vat_on_payment_account2logs[sale_vat_account]
            # and also for taxedop_type2logs['france']
            for log in vat_on_payment_account2logs[sale_vat_account]:
                base_log = dict(log)
                vat_amount = log["amount"]
                base = speedy["currency"].round(vat_amount * 10000 / rate_int)
                base_log["amount"] = base
                taxedop_type2logs["france"].append(base_log)
        # MONACO
        monaco_logs = self._generate_due_vat_monaco(speedy, sale_vat_accounts)
        return monaco_logs

    def _generate_due_vat_autoliq(self, speedy, rate2logs, taxedop_type2logs):
        (
            autoliq_taxedop_type2accounts,
            autoliq_vat_accounts,
            autoliq_vat_account2rate,
            autoliq_tax2rate,
        ) = self._generate_due_vat_prepare_autoliq_struct(speedy)
        # compute bloc "B décompte de la TVA à payer"
        self._generate_due_vat_autoliq_vat_to_pay(
            speedy, autoliq_vat_account2rate, rate2logs
        )
        # compute bloc "opérations imposables"
        # Extracom
        self._generate_due_vat_taxed_op_extracom(
            speedy,
            autoliq_vat_account2rate,
            autoliq_taxedop_type2accounts,
            taxedop_type2logs,
        )

        # Intracom
        rate2product_ratio = self._compute_rate2product_ratio(
            speedy, autoliq_taxedop_type2accounts, autoliq_tax2rate
        )

        autoliq_intracom_product_logs = self._generate_due_vat_intracom_taxed_op(
            speedy,
            autoliq_vat_account2rate,
            autoliq_taxedop_type2accounts,
            rate2product_ratio,
            taxedop_type2logs,
        )
        return autoliq_intracom_product_logs

    def _generate_due_vat_prepare_autoliq_struct(self, speedy):
        autoliq_taxedop_type2accounts = {
            "intracom_b2b": speedy["aa_obj"],
            "extracom": speedy["aa_obj"],
        }
        autoliq_vat_account2rate = {}
        autoliq_tax2rate = {}
        autoliq_vat_accounts = speedy["aa_obj"]
        autoliq_vat_taxes = speedy["at_obj"].search(
            [
                ("type_tax_use", "=", "purchase"),
                ("amount_type", "=", "percent"),
                ("amount", ">", 0),
                ("fr_vat_autoliquidation", "=", True),
                ("company_id", "=", speedy["company_id"]),
            ]
        )
        for tax in autoliq_vat_taxes:
            lines = tax.invoice_repartition_line_ids.filtered(
                lambda x: x.repartition_type == "tax"
                and x.account_id
                and int(x.factor_percent) == -100
            )
            if len(lines) != 1:
                raise UserError(_("A regular sale "))
            account = lines.account_id
            rate_int = int(tax.amount * 100)
            autoliq_tax2rate[tax] = rate_int
            if (
                account in autoliq_vat_account2rate
                and autoliq_vat_account2rate[account] != rate_int
            ):
                raise UserError(
                    _(
                        "Account '%s' is used as due VAT account on several "
                        "auto-liquidation taxes for different rates "
                        "(%.2f%% and %.2f%%)."
                    )
                    % (
                        account.display_name,
                        rate_int / 100,
                        autoliq_vat_account2rate[account] / 100,
                    )
                )
            autoliq_vat_account2rate[account] = rate_int
            autoliq_vat_accounts |= account
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
                        "Auto-liquidation tax '%s' is not present in the tax mapping "
                        "of any fiscal position."
                    )
                    % tax.display_name
                )
            fr_vat_type = tax_map.position_id.fr_vat_type
            autoliq_taxedop_type2accounts[fr_vat_type] |= account
        return (
            autoliq_taxedop_type2accounts,
            autoliq_vat_accounts,
            autoliq_vat_account2rate,
            autoliq_tax2rate,
        )

    def _generate_due_vat_autoliq_vat_to_pay(
        self, speedy, autoliq_vat_account2rate, rate2logs
    ):
        # Generate autoliq logs for boxes 08, 09, 9A
        # For autoliq, we don't do VAT on payment, we do VAT on debit
        # Check that these autoliq due accounts 4452xx are empty at start of period
        for account, rate_int in autoliq_vat_account2rate.items():
            # check start balance is empty at start of period
            # This check is important because, for intracom autoliq,
            # we analyse each invoice for the product/service ratio,
            # so it won't work if the autoliq due account has a residual amount
            # at start of period (and if we allow that, we get all sorts of problem:
            # for example, when the intracom due account has a residual at start
            # of period but there are no intracom autoliq invoice in the period, so
            # our dicts rate2product_ratio are empty)
            balance_end_previous_period = account._fr_vat_get_balance(
                "base_domain_end_previous", speedy
            )
            if not speedy["currency"].is_zero(balance_end_previous_period):
                raise UserError(
                    _(
                        "Account '%s' is a due VAT auto-liquidation account. "
                        "So it should be empty at the start of the VAT period, "
                        "but the balance on the last day of the previous period is %s."
                    )
                    % (
                        account.display_name,
                        format_amount(
                            self.env, balance_end_previous_period, speedy["currency"]
                        ),
                    )
                )
            balance = account._fr_vat_get_balance("base_domain_end", speedy) * -1
            if not speedy["currency"].is_zero(balance):
                rate2logs[rate_int].append(
                    {
                        "account_id": account.id,
                        "compute_type": "balance",
                        "amount": balance,
                    }
                )

    def _generate_due_vat_taxed_op_extracom(
        self,
        speedy,
        autoliq_vat_account2rate,
        autoliq_taxedop_type2accounts,
        taxedop_type2logs,
    ):
        # Taxable operations - Autoliquidation Extra EU
        # Box 3B: Achats de biens ou presta de services réalisés auprès d'un
        # assujetti non établi en France (art 283-1 du CGI)
        for account in autoliq_taxedop_type2accounts["extracom"]:
            vat_amount = account._fr_vat_get_balance("base_domain_end", speedy) * -1
            if not speedy["currency"].is_zero(vat_amount):
                rate_int = autoliq_vat_account2rate[account]
                base = speedy["currency"].round(vat_amount * 10000 / rate_int)
                taxedop_type2logs["autoliq_extracom"].append(
                    {
                        "account_id": account.id,
                        "compute_type": "computed_base",
                        "amount": base,
                        "note": _("VAT Amount %s, Rate %.2f%%, Base %s")
                        % (
                            format_amount(self.env, vat_amount, speedy["currency"]),
                            rate_int / 100,
                            format_amount(self.env, base, speedy["currency"]),
                        ),
                    }
                )

    def _generate_due_vat_intracom_taxed_op(
        self,
        speedy,
        autoliq_vat_account2rate,
        autoliq_taxedop_type2accounts,
        rate2product_ratio,
        taxedop_type2logs,
    ):
        # Compute boxes A3, B2 and 17
        autoliq_intracom_product_logs = []  # for box 17

        for account in autoliq_taxedop_type2accounts["intracom_b2b"]:
            vat_amount = account._fr_vat_get_balance("base_domain_end", speedy) * -1
            if not speedy["currency"].is_zero(vat_amount):
                rate_int = autoliq_vat_account2rate[account]
                product_ratio = rate2product_ratio[rate_int]
                service_ratio = 100 - product_ratio
                base = speedy["currency"].round(vat_amount * 10000 / rate_int)
                product_base = 0
                if not float_is_zero(product_ratio, precision_digits=2):
                    # Box B2
                    product_base = round(base * product_ratio / 100, 2)
                    taxedop_type2logs["autoliq_intracom_product"].append(
                        {
                            "account_id": account.id,
                            "compute_type": "computed_base",
                            "amount": product_base,
                            "note": _(
                                "VAT Amount %s, Rate %.2f%%, Base %s, "
                                "Product Ratio %.2f%%, Product Base %s"
                            )
                            % (
                                format_amount(self.env, vat_amount, speedy["currency"]),
                                rate_int / 100,
                                format_amount(self.env, base, speedy["currency"]),
                                product_ratio,
                                format_amount(
                                    self.env, product_base, speedy["currency"]
                                ),
                            ),
                        }
                    )
                    # Box 17
                    product_vat_amount = round(vat_amount * product_ratio / 100, 2)
                    autoliq_intracom_product_logs.append(
                        {
                            "account_id": account.id,
                            "compute_type": "computed_vat_amount",
                            "amount": product_vat_amount,
                            "note": _(
                                "VAT amount %s, Product Ratio %.2f%%, "
                                "VAT Product Amount %s"
                            )
                            % (
                                format_amount(self.env, vat_amount, speedy["currency"]),
                                product_ratio,
                                format_amount(
                                    self.env, product_vat_amount, speedy["currency"]
                                ),
                            ),
                        }
                    )

                # Box A3
                service_base = round(base - product_base, 2)
                if not float_is_zero(service_base, precision_digits=2):
                    taxedop_type2logs["autoliq_intracom_service"].append(
                        {
                            "account_id": account.id,
                            "compute_type": "computed_base",
                            "amount": service_base,
                            "note": _(
                                "VAT Amount %s, Rate %.2f%%, Base %s, "
                                "Service Ratio %.2f%%, Service Base %s"
                            )
                            % (
                                format_amount(self.env, vat_amount, speedy["currency"]),
                                rate_int / 100,
                                format_amount(self.env, base, speedy["currency"]),
                                service_ratio,
                                format_amount(
                                    self.env, service_base, speedy["currency"]
                                ),
                            ),
                        }
                    )
        return autoliq_intracom_product_logs

    def _compute_rate2product_ratio(
        self, speedy, autoliq_taxedop_type2accounts, autoliq_tax2rate
    ):
        rate2total = defaultdict(float)
        rate2product = defaultdict(float)
        autoliq_vat_move_lines = speedy["aml_obj"].search(
            [
                ("account_id", "in", autoliq_taxedop_type2accounts["intracom_b2b"].ids),
                ("balance", "!=", 0),
            ]
            + speedy["base_domain_period"]
        )

        autoliq_vat_moves = autoliq_vat_move_lines.move_id
        product_account_prefixes = self._get_product_account_prefixes()
        for move in autoliq_vat_moves:
            if move.move_type not in ("in_invoice", "in_refund"):
                raise UserError(
                    _(
                        "Journal entry '%s' uses an intracom autoliquidation due VAT "
                        "account but is not a supplier invoice/refund. "
                        "This scenario is not supported."
                    )
                    % move.display_name
                )
            for line in move.invoice_line_ids.filtered(lambda x: not x.display_type):
                rate_int = 0
                for tax in line.tax_ids:
                    if tax in autoliq_tax2rate:
                        rate_int = autoliq_tax2rate[tax]
                if rate_int:
                    rate2total[rate_int] += line.balance
                    # If we have a product, we use its type and is_accessory_cost
                    # to determine if it's a product or service
                    # If we don't have a product, we use the account
                    if line.product_id:
                        if (
                            line.product_id.type in ("product", "consu")
                            or line.product_id.is_accessory_cost
                        ):
                            rate2product[rate_int] += line.balance
                    else:
                        if line.account_id.code.startswith(product_account_prefixes):
                            rate2product[rate_int] += line.balance

        rate2product_ratio = {}
        for rate_int, total in rate2total.items():
            productratio = 0
            if not speedy["currency"].is_zero(total):
                productratio = round(100 * rate2product[rate_int] / total, 2)
            rate2product_ratio[rate_int] = productratio

        return rate2product_ratio

    @api.model
    def _get_product_account_prefixes(self):
        return (
            "21",
            "601",
            "602",
            "605",
            "606",
            "607",
            "6091",
            "6092",
            "6095",
            "6096",
            "6097",
            "6181",
            "6183",
            "6232",
            "6234",
            "6236",
        )

    def _generate_due_vat_create_vat_to_pay_lines(self, speedy, rate2logs):
        # Create boxes 08, 09, 9B (columns base HT et Taxe due)
        rate2box = {}  # rate as integer x 100 i.e. 550 for 5,5%
        due_vat_boxes = speedy["box_obj"].search(
            [
                ("box_type", "=", "due_vat"),
                ("due_vat_rate", ">", 0),
                ("due_vat_base_box_id", "!=", False),
            ]
        )
        for due_vat_box in due_vat_boxes:
            rate2box[int(due_vat_box.due_vat_rate)] = due_vat_box
        if not rate2box:
            raise UserError(
                _(
                    "Problem in the configuration of the due VAT boxes. "
                    "This should never happen."
                )
            )

        for rate_int, logs in rate2logs.items():
            if logs:
                if rate_int not in rate2box:
                    raise UserError(
                        _("No Due VAT box found for VAT rate %.2f%%.") % rate_int / 100
                    )
                box = rate2box[rate_int]
                vals = {
                    "parent_id": self.id,
                    "box_id": box.id,
                    "log_ids": [(0, 0, x) for x in logs],
                }
                line = speedy["line_obj"].create(vals)
                box_base = box.due_vat_base_box_id
                rate = rate_int / 100
                base_vals = {
                    "parent_id": self.id,
                    "box_id": box_base.id,
                    "log_ids": [
                        (
                            0,
                            0,
                            {
                                "compute_type": "rate",
                                "amount": line.value_float * 100 / rate,
                                "note": "VAT Amount %s, Rate %.2f%%, "
                                "Base = VAT Amount / Rate"
                                % (
                                    format_amount(
                                        self.env, line.value_float, speedy["currency"]
                                    ),
                                    rate,
                                ),
                            },
                        )
                    ],
                }
                speedy["line_obj"].create(base_vals)

    def _generate_due_vat_monaco(self, speedy, sale_vat_accounts):
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
                ("account_id", "in", sale_vat_accounts.ids),
                ("balance", "!=", 0),
            ]
            + speedy["base_domain_period"]
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
                    "note": _("Monaco customer '%s', VAT amount %s")
                    % (
                        mline.partner_id.display_name,
                        format_amount(self.env, vat_amount, speedy["currency"]),
                    ),
                }
            )
        return monaco_box_logs

    def _create_line(self, speedy, logs, box_type):
        if logs:
            vals = {
                "parent_id": self.id,
                "box_id": speedy["box_obj"]._box_from_single_box_type(box_type).id,
                "log_ids": [(0, 0, x) for x in logs],
            }
            speedy["line_obj"].create(vals)

    def _vat_on_payment(self, in_or_out, vat_account_ids, speedy):
        assert in_or_out in ("in", "out")
        account2logs = defaultdict(list)
        common_move_domain = speedy["company_domain"] + [
            ("date", "<=", self.end_date),
            ("amount_total", ">", 0),
        ]
        if in_or_out == "in":
            journal_type = "purchase"
            vat_sign = -1
            account_type = "payable"
            common_move_domain += [
                ("move_type", "in", ("in_invoice", "in_refund")),
                ("fiscal_position_fr_vat_type", "=", "france_vendor_vat_on_payment"),
            ]
        elif in_or_out == "out":
            journal_type = "sale"
            vat_sign = 1
            account_type = "receivable"
            common_move_domain += [
                ("out_vat_on_payment", "=", True),
                ("move_type", "in", ("out_invoice", "out_refund")),
                (
                    "fiscal_position_fr_vat_type",
                    "in",
                    (False, "france", "france_vendor_vat_on_payment"),
                ),
            ]
        # The goal of this method is to "remove" on_payment invoices that were unpaid
        # on self.end_date
        # Several cases :
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

        # Case 1. unpaid invoices
        unpaid_invs = speedy["am_obj"].search(
            common_move_domain + [("payment_state", "=", "not_paid")]
        )
        for unpaid_inv in unpaid_invs:
            for line in unpaid_inv.line_ids.filtered(
                lambda x: not x.display_type and x.account_id.id in vat_account_ids
            ):
                amount = speedy["currency"].round(line.balance) * vat_sign
                note = _(
                    "Invoice/refund is unpaid, Unpaid VAT amount %s"
                ) % format_amount(self.env, amount, speedy["currency"])
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
            speedy["company_domain"] + [("internal_type", "=", account_type)]
        )
        # I want reconcile marks after first day of current month
        # But, to avoid trouble with timezones, I use '>=' self.end_date (and not '>')
        # It's not a problem if we have few additionnal invoices to analyse
        full_reconcile_post_end = self.env["account.full.reconcile"].search(
            [("create_date", ">=", self.end_date)]
        )
        reconciled_purchase_or_sale_lines = speedy["aml_obj"].search(
            speedy["company_domain"]
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
            for payment in move._get_reconciled_info_JSON_values():
                if payment["date"] <= self.end_date and payment["amount"]:
                    unpaid_amount -= payment["amount"]
                    fully_unpaid = False
            # If invoice is not fully paid on end_date, compute an unpaid ratio
            if not move.currency_id.is_zero(unpaid_amount):
                unpaid_ratio = unpaid_amount / move.amount_total
                for line in move.line_ids.filtered(
                    lambda x: not x.display_type and x.account_id.id in vat_account_ids
                ):
                    balance = line.balance * vat_sign
                    if fully_unpaid:
                        amount = speedy["currency"].round(balance)
                        note = _(
                            "Invoice/refund was unpaid on %s, Unpaid VAT amount %s"
                        ) % (
                            speedy["end_date_formatted"],
                            format_amount(self.env, amount, speedy["currency"]),
                        )
                    else:
                        amount = speedy["currency"].round(balance * unpaid_ratio)
                        note = _(
                            "%d%% of the invoice/refund was unpaid on %s, "
                            "VAT amount %s => Unpaid VAT amount %s"
                        ) % (
                            int(round(unpaid_ratio * 100)),
                            speedy["end_date_formatted"],
                            format_amount(self.env, balance, speedy["currency"]),
                            format_amount(self.env, amount, speedy["currency"]),
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
        boxtype2vat_accounts = {
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
        for (account, vtype) in vat_account2type.items():
            if vtype in ("asset", "regular"):
                vat_payment_deduc_accounts |= account

        # Generate logs for vat_on_payment supplier invoices
        vat_on_payment_account2logs = self._vat_on_payment(
            "in", vat_payment_deduc_accounts.ids, speedy
        )

        # Generate return line for the 2 deduc VAT boxes
        for box_type, vat_accounts in boxtype2vat_accounts.items():
            logger.info(
                "Deduc VAT accounts: %s go to box type %s",
                ", ".join([x.code for x in vat_accounts]),
                box_type,
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
                logs += vat_on_payment_account2logs[vat_account]
            self._create_line(speedy, logs, box_type)

    def _generate_deductible_vat_prepare_struct(self, speedy):
        vat_account2type = {}
        deduc_vat_taxes = speedy["at_obj"].search(
            speedy["company_domain"]
            + [
                ("amount_type", "=", "percent"),
                ("amount", ">", 0),
                ("type_tax_use", "=", "purchase"),
            ]
        )
        for tax in deduc_vat_taxes:
            line = tax.invoice_repartition_line_ids.filtered(
                lambda x: x.repartition_type == "tax"
                and x.account_id
                and int(x.factor_percent) == 100
            )
            if len(line) != 1:
                raise UserError(
                    _("Bad configuration on regular purchase tax '%s'.")
                    % tax.display_name
                )
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
                            "Very strange, it should start with 44566."
                            % vat_account.code
                        )
            if (
                vat_account in vat_account2type
                and vat_account2type[vat_account] != vtype
            ):
                raise UserError(
                    _(
                        "Account '%s' is used for several kinds of "
                        "deductible VAT taxes (%s and %s)."
                    )
                    % (vat_account.display_name, vtype, vat_account2type[vat_account])
                )
            vat_account2type[vat_account] = vtype

        logger.info(
            "Deduc VAT accounts: %s"
            % ", ".join(
                [
                    "%s (%s)" % (acc.code, vtype)
                    for (acc, vtype) in vat_account2type.items()
                ]
            )
        )
        return vat_account2type

    def _generate_operation_untaxed(self, speedy):
        self.ensure_one()
        fp_types = ["intracom_b2b", "intracom_b2c", "extracom", "france_exo"]
        fpositions2boxtype = {}
        for fp_type in fp_types:
            box_type = "untaxed_op_%s" % fp_type
            fpositions = speedy["afp_obj"].search(
                speedy["company_domain"] + [("fr_vat_type", "=", fp_type)]
            )
            fpositions2boxtype[fpositions] = box_type
        boxtype2accounts = {}
        for fpositions, box_type in fpositions2boxtype.items():
            for fposition in fpositions:
                if not fposition.account_ids:
                    raise UserError(
                        _("Missing account mapping on fiscal position '%s'.")
                        % fposition.display_name
                    )
                for mapping in fposition.account_ids:
                    if box_type not in boxtype2accounts:
                        boxtype2accounts[box_type] = mapping.account_dest_id
                    else:
                        boxtype2accounts[box_type] |= mapping.account_dest_id
        # check that an account is not present in several fiscal positions
        # and create lines
        account_unicity = []
        for (box_type, accounts) in boxtype2accounts.items():
            if account_unicity:
                for acc in accounts:
                    if acc.id in account_unicity:
                        raise UserError(
                            _(
                                "Account '%s' is present in the mapping of several "
                                "fiscal positions."
                            )
                            % acc.display_name
                        )
            account_unicity += accounts.ids
            # create the declaration lines
            logs = []
            for account in accounts:
                balance = account._fr_vat_get_balance("base_domain_period", speedy)
                if not speedy["currency"].is_zero(balance):
                    logs.append(
                        {
                            "amount": balance * -1,
                            "account_id": account.id,
                            "compute_type": "period_balance",
                        }
                    )
            self._create_line(speedy, logs, box_type)

    def _switch_negative_boxes(self, speedy):
        negative_lines = speedy["line_obj"].search(
            [
                ("value", "<", 0),
                ("box_edi_type", "=", "MOA"),
                ("parent_id", "=", self.id),
            ]
        )
        logger.info("%d negative lines detected", len(negative_lines))
        for line in negative_lines:
            # delete negative due VAT base lines
            if line.box_box_type == "due_vat_base":
                line.unlink()
                continue
            negative_box = line.box_id.negative_switch_box_id
            if not negative_box:
                raise UserError(
                    _(
                        "Box '%s' has a negative value (%s) but it doesn't have a "
                        "negative switch box."
                    )
                    % (line.box_id.display_name, line.value)
                )
            negative_line = speedy["line_obj"].search(
                [
                    ("parent_id", "=", self.id),
                    ("box_id", "=", negative_box.id),
                ],
                limit=1,
            )
            if not negative_line:
                negative_line = speedy["line_obj"].create(
                    {
                        "box_id": negative_box.id,
                        "parent_id": self.id,
                        "negative_switch": True,
                    }
                )
            # Transfer log line to the negative box line
            for log in line.log_ids:
                vals = {
                    "parent_id": negative_line.id,
                }
                log.write(vals)
            line.unlink()

    def create_reimbursement_line(self, amount):
        assert isinstance(amount, int)
        assert amount > 0
        speedy = self._prepare_speedy()
        box = self.env["l10n.fr.account.vat.box"]._box_from_single_box_type(
            "vat_reimbursement"
        )
        account_id = self._get_box_account(box).id
        log_vals = {
            "amount": amount,
            "compute_type": "manual",
            "account_id": account_id,
        }
        vals = {"box_id": box.id, "parent_id": self.id, "log_ids": [(0, 0, log_vals)]}
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
            [("box_box_type", "=", "vat_reimbursement"), ("parent_id", "=", self.id)]
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

    def _prepare_account_move(self, speedy):
        self.ensure_one()
        if not self.company_id.fr_vat_journal_id:
            raise UserError(
                _("Journal for VAT Journal Entry is not set on company '%s'.")
                % self.company_id.display_name
            )
        self._get_adjust_accounts(speedy)
        lvals_list = []
        total = 0.0
        account2amount = defaultdict(float)
        for line in self.line_ids.filtered(lambda x: x.box_accounting_method):
            method = line.box_accounting_method
            sign = method == "credit" and 1 or -1
            if line.box_box_type == "manual" and line.value_manual_int:
                account = self._get_box_account(line.box_id, raise_if_none=True)
                account2amount[(account, line.manual_analytic_account_id)] += (
                    line.value_manual_int * sign
                )
            else:
                for log in line.log_ids:
                    assert log.account_id  # there is a python constrain on this
                    amount = log.amount * sign
                    # Special case for for VAT credit account 44567:
                    # we don't want to group
                    if log.account_id.code.startswith("44567"):
                        lvals = {
                            "account_id": log.account_id.id,
                            "analytic_account_id": log.analytic_account_id.id or False,
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
                            (log.account_id, log.analytic_account_id)
                        ] += amount
        for (account, analytic_account), amount in account2amount.items():
            amount = speedy["currency"].round(amount)
            total += amount
            compare = speedy["currency"].compare_amounts(amount, 0)
            lvals = {
                "account_id": account.id,
                "analytic_account_id": analytic_account
                and analytic_account.id
                or False,
            }
            if compare > 0:
                lvals["credit"] = amount
                lvals_list.append(lvals)
            elif compare < 0:
                lvals["debit"] = -amount
                lvals_list.append(lvals)
            logger.debug("VAT move account %s: %s", account.code, lvals)
        total_compare = speedy["currency"].compare_amounts(total, 0)
        total = speedy["currency"].round(total)
        if total_compare > 0:
            lvals_list.append(
                {
                    "debit": total,
                    "account_id": speedy["expense_adjust_account"].id,
                    "analytic_account_id": self.company_id.fr_vat_expense_analytic_account_id.id
                    or False,
                }
            )
        elif total_compare < 0:
            lvals_list.append(
                {
                    "credit": -total,
                    "account_id": speedy["income_adjust_account"].id,
                    "analytic_account_id": self.company_id.fr_vat_income_analytic_account_id.id
                    or False,
                }
            )

        vals = {
            "date": self.end_date,
            "journal_id": self.company_id.fr_vat_journal_id.id,
            "ref": "CA3 %s" % self.display_name,
            "company_id": speedy["company_id"],
            "line_ids": [(0, 0, x) for x in lvals_list],
        }
        return vals

    def _reconcile_account_move(self, move, speedy):
        excluded_lines = speedy["log_obj"].search_read(
            [
                ("parent_parent_id", "=", self.id),
                ("origin_move_id", "!=", False),
                ("compute_type", "=", "unpaid_vat_on_payment"),
            ],
            ["origin_move_id"],
        )
        excluded_line_ids = [x["origin_move_id"][0] for x in excluded_lines]
        for line in move.line_ids.filtered(lambda x: x.account_id.reconcile):
            account = line.account_id
            domain = speedy["base_domain_end"] + [
                ("account_id", "=", account.id),
                ("full_reconcile_id", "=", False),
                ("move_id", "not in", excluded_line_ids),
            ]
            rg_res = speedy["aml_obj"].read_group(domain, ["balance"], [])
            # or 0 is need to avoid a crash: rg_res[0]["balance"] = None
            # when the moves are already reconciled
            if rg_res and speedy["currency"].is_zero(rg_res[0]["balance"] or 0):
                moves_to_reconcile = speedy["aml_obj"].search(domain)
                moves_to_reconcile.reconcile()

    def _create_draft_account_move(self, speedy):
        self.ensure_one()
        assert self.state in ("manual", "auto")
        if not self.line_ids.filtered(lambda x: not x.box_display_type):
            raise UserError(
                _("The declaration %s doesn't contain any line.") % self.display_name
            )
        move = speedy["am_obj"].create(self._prepare_account_move(speedy))
        return move

    def _get_box_account(self, box, raise_if_none=True):
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
                        "You may want to setup a specific account on that box."
                    )
                    % box.display_name
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
                        "Box '%s' is configured with Manual Account Code '%s', "
                        "but there are no accounts that start with this code in "
                        "company '%s'. You may want to setup a specific account "
                        "on that box."
                    )
                    % (box.display_name, box.account_code, self.company_id.display_name)
                )
            return None
        if len(accounts) > 1:
            logger.warning(
                "There are %d accounts that start with '%s' in company %s",
                len(accounts),
                box.account_code,
                self.company_id.display_name,
            )
        return accounts[0]

    def unlink(self):
        for rec in self:
            if rec.state != "manual":
                raise UserError(
                    _(
                        "Cannot delete VAT return '%s' because it is not in "
                        "'Manual Lines' state."
                    )
                    % rec.display_name
                )
        return super().unlink()

    def generate_selenium_file(self):
        self.ensure_one()
        name = "CA3-%s" % self.display_name
        if self.vat_periodicity != "1":
            raise UserError(
                _("Selenium export only support monthly CA3 returns for the moment.")
            )
        if self.line_ids.filtered(
            lambda x: x.box_form_code == "3310A" and not x.box_display_type
        ):
            raise UserError(_("Selenium cannot work when there are 3310-A lines."))
        month2label = {  # I don't want to fight with locales
            1: "Janvier",
            2: "Février",
            3: "Mars",
            4: "Avril",
            5: "Mai",
            6: "Juin",
            7: "Juillet",
            8: "Août",
            9: "Septembre",
            10: "Octobre",
            11: "Novembre",
            12: "Décembre",
        }
        period_name = "%s %s" % (
            month2label[self.start_date.month],
            self.start_date.year,
        )
        if not self.company_id.siret:
            raise UserError(
                _("Missing SIRET on company '%s'.") % self.company_id.display_name
            )
        # TODO: move Selenium file generation to a python lib ?
        siren = self.company_id.siret[:9]
        siren_with_spaces = " ".join([siren[:3], siren[3:6], siren[6:9]])
        test_uuid = str(uuid.uuid4())
        side_dict = {
            "id": str(uuid.uuid4()),
            "version": "2.0",
            "name": name,
            "url": "https://www.impots.gouv.fr",
            "tests": [
                {
                    "id": test_uuid,
                    "name": name,
                    "commands": [
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Slower speed to see pages",
                            "command": "setSpeed",
                            "target": "1000",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Open impots.gouv.fr/portail",
                            "command": "open",
                            "target": "/portail/",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Click on Votre espace professionnel",
                            "command": "click",
                            "target": "css=.identificationpro > span",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Click on TVA",
                            "command": "click",
                            "target": "linkText=TVA",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Check SIREN %s" % siren,
                            "command": "assertText",
                            "target": "xpath=//table[@class='selection']//tr[2]/td[2]/strong",
                            # xpath //table[@class='selection']/tr[2]/td[2]/strong doesn't work
                            # although it is what you have in the HTML of the page
                            # because the browser (?) auto-adds <tbody> between table and tr
                            "value": siren,
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Click on Déclarer",
                            "command": "click",
                            "target": "name=button.submitValider",
                            "opensWindow": True,
                            "windowHandleName": "new_vat_tab",
                            "windowTimeout": 2000,
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Identify new tab",
                            "command": "storeWindowHandle",
                            "target": "root",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Switch to new tab",
                            "command": "selectWindow",
                            "target": "handle=${new_vat_tab}",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Click on %s" % period_name,
                            "command": "click",
                            "target": "linkText=%s" % period_name,
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Higher speed for VAT form",
                            "command": "setSpeed",
                            "target": "0",
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Check SIREN %s" % siren,
                            "command": "assertText",
                            "target": "xpath=//div[contains(.,'SIREN')]/span",
                            "value": siren_with_spaces,
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "comment": "Check period %s" % period_name,
                            "command": "assertText",
                            "target": "xpath=//div[contains(.,'imposition')]/following::div",
                            "value": period_name,
                        },
                    ],
                }
            ],
            "suites": [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Default Suite",
                    "persistSession": False,
                    "parallel": False,
                    "timeout": 300,
                    "tests": [test_uuid],
                }
            ],
            "urls": ["https://www.impots.gouv.fr/"],
            "plugins": [],
        }

        push_box_ids = {}
        for pbox in self.env["l10n.fr.account.vat.box"].search(
            [("push_box_id", "!=", False)]
        ):
            push_box_ids[pbox.push_box_id.id] = True

        for line in self.line_ids:
            box = line.box_id
            if (
                not line.box_display_type
                and box.box_type != "due_vat"
                and box.id not in push_box_ids
            ):
                if not box.nref_code:
                    raise UserError(_("Missing NREF code on box '%s'." % box.name))
                # if box.edi_type != 'MOA':
                nref_code = box.nref_code
                value = line.value
                if box.edi_type == "MOA":
                    click_dict = {
                        "id": str(uuid.uuid4()),
                        "comment": "Select %s" % box.display_name,
                        "command": "click",
                        "target": "id=A%s_0" % nref_code,
                        "value": "",
                    }
                    side_dict["tests"][0]["commands"].append(click_dict)
                    type_dict = {
                        "id": str(uuid.uuid4()),
                        "comment": "Write %d in %s" % (value, box.display_name),
                        "command": "type",
                        "target": "id=A%s_0" % nref_code,
                        "value": "%d" % value,
                    }
                    side_dict["tests"][0]["commands"].append(type_dict)
                # elif box.edi_type == 'CCI_TBX' and value:
                #    click_dict = {
                #        "id": str(uuid.uuid4()),
                #        "comment": "Check box %s" % box.display_name,
                #        "command": "click",
                #        "target": "xpath=//input[@id='A%s_0']" % nref_code,
                #        "value": "",
                #        }
                #    side_dict['tests'][0]['commands'].append(click_dict)
                else:
                    raise UserError(
                        _(
                            "Only MOA fields can be exported to Selenium for the "
                            "moment. It is not the case of box '%s'."
                        )
                        % box.display_name
                    )

        side_str = json.dumps(side_dict, ensure_ascii=False)
        side_bytes = side_str.encode("utf-8")

        filename = "selenium_%s.side" % name
        attach = self.env["ir.attachment"].create(
            {
                "name": filename,
                "res_id": self.id,
                "res_model": self._name,
                "raw": side_bytes,
            }
        )
        self.write({"selenium_attachment_id": attach.id})
        action = {
            "name": _("Selenium IDE File"),
            "type": "ir.actions.act_url",
            "url": "web/content/?model=%s&id=%d&filename_field=selenium_attachment_name&"
            "field=selenium_attachment_datas&download=true&filename=%s"
            % (self._name, self.id, filename),
            "target": "new",
        }
        return action

    def print_ca3(self):
        self.ensure_one()
        # In manu/auto, we re-generate it every time because comment_dgfip
        # may have changed
        if self.ca3_attachment_id and self.state in ("manual", "auto"):
            self.ca3_attachment_id.unlink()
        if not self.ca3_attachment_id:
            self.generate_ca3_attachment()
        action = {
            "name": "FEC",
            "type": "ir.actions.act_url",
            "url": "web/content/?model=%s&id=%d&filename_field=ca3_attachment_name&"
            "field=ca3_attachment_datas&download=true&filename=%s"
            % (self._name, self.id, self.ca3_attachment_name),
            "target": "new",
            # target: "new" and NOT "self", otherwise you get the following bug:
            # after this action, all UserError won't show a pop-up to the user
            # but will only show a warning message in the logs until the web
            # page is reloaded
        }
        return action

    def generate_ca3_attachment(self):
        packet1 = io.BytesIO()
        packet2 = io.BytesIO()
        packet3 = io.BytesIO()
        # create a new PDF that contains the additional text with Reportlab
        page2canvas = {
            "1": canvas.Canvas(packet1, pagesize=A4),
            "2": canvas.Canvas(packet2, pagesize=A4),
            "3": canvas.Canvas(packet3, pagesize=A4),
        }
        page2canvas["1"].setFont("Helvetica", 10)
        page2canvas["2"].setFont("Helvetica", 8)
        page2canvas["3"].setFont("Helvetica", 8)

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
                raise UserError(_("EDI type not supported for box '%s'.") % box.name)

            if pdf_value:
                page2canvas[box.print_page].drawRightString(
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
                page2canvas["1"].drawString(pvals["x"], pvals["y"], pvals["value"])
        # Comment => block of text
        if self.comment_dgfip:
            text_object = page2canvas["1"].beginText(21, 290)
            for line in self.comment_dgfip.splitlines():
                line_wrapped = textwrap.wrap(
                    line, width=120, break_long_words=False, replace_whitespace=False
                )
                for wline in line_wrapped:
                    text_object.textLine(wline.rstrip())
            page2canvas["1"].drawText(text_object)
        # Address => use flowable because it is multiline
        addr = self.company_id.partner_id._display_address(without_company=True)
        if addr:
            styleSheet = getSampleStyleSheet()
            style = styleSheet["BodyText"]
            style.fontSize = 8
            style.leading = 9
            addr_para = Paragraph(addr.replace("\n", "<br/>"), style)
            addr_para.wrap(570 - 282, 636 - 602)
            addr_para.drawOn(page2canvas["1"], 282, 602)
        for canv in page2canvas.values():
            canv.save()

        # move to the beginning of the StringIO buffer
        packet1.seek(0)
        packet2.seek(0)
        packet3.seek(0)
        watermark_pdf_reader_p1 = PdfFileReader(packet1)
        watermark_pdf_reader_p2 = PdfFileReader(packet2)
        watermark_pdf_reader_p3 = PdfFileReader(packet3)
        # read your existing PDF
        ca3_original_fd = tools.file_open(
            "l10n_fr_account_vat_return/report/CA3_cerfa.pdf", "rb"
        )
        ca3_original_reader = PdfFileReader(ca3_original_fd)
        ca3_writer = PdfFileWriter()
        # add the "watermark" (which is the new pdf) on the existing page
        page1 = ca3_original_reader.getPage(0)
        page2 = ca3_original_reader.getPage(1)
        page3 = ca3_original_reader.getPage(2)
        page1.mergePage(watermark_pdf_reader_p1.getPage(0))
        page2.mergePage(watermark_pdf_reader_p2.getPage(0))
        page3.mergePage(watermark_pdf_reader_p3.getPage(0))
        ca3_writer.addPage(page1)
        ca3_writer.addPage(page2)
        ca3_writer.addPage(page3)
        # finally, write "output" to a real file
        out_ca3_io = io.BytesIO()
        ca3_writer.write(out_ca3_io)
        out_ca3_bytes = out_ca3_io.getvalue()
        ca3_original_fd.close()

        filename = "CA3_%s.pdf" % self.display_name
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
    box_box_type = fields.Selection(related="box_id.box_type", store=True)
    box_name = fields.Char(related="box_id.name", store=True)
    box_display_type = fields.Selection(related="box_id.display_type", store=True)
    box_sequence = fields.Integer(related="box_id.sequence", store=True)
    negative_switch = fields.Boolean(readonly=True)
    value = fields.Integer(
        compute="_compute_value", store=True
    )  # MOA, QTY, PCD, CCI_TBX (manual + auto)
    value_float = fields.Float(
        compute="_compute_value", store=True, string="Value Before Rounding"
    )  # MOA, QTY, PCD (auto)
    value_bool = fields.Boolean(string="Value (Y/N)")  # CCI_TBX (manual + auto)
    value_manual_int = fields.Integer(string="Integer Value")  # MOA, QTY, PCD (manual)
    value_char = fields.Char(string="Text")  # FTX (manual + auto), except for BA field
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
    )
    manual_analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        compute="_compute_manual_account_id",
        check_company=True,
    )

    # idea: field value_tree type fields.Char() that would agregate
    # all types (adding € sign for MOA) and be used in tree view
    # but the content would be aligned on the right => not so good idea...

    _sql_constraints = [
        ("unique_return_box", "unique(parent_id, box_id)", "This line already exists!")
    ]

    @api.depends("box_id")
    def _compute_manual_account_id(self):
        for line in self:
            manual_account_id = False
            manual_analytic_account_id = False
            if line.box_id and line.box_id.box_type == "manual" and line.parent_id:
                account = line.parent_id._get_box_account(
                    line.box_id, raise_if_none=False
                )
                if account:
                    manual_account_id = account.id
                manual_analytic_account_id = (
                    line.with_company(
                        line.parent_id.company_id.id
                    ).box_id.analytic_account_id.id
                    or False
                )
            line.manual_account_id = manual_account_id
            line.manual_analytic_account_id = manual_analytic_account_id

    @api.constrains("value_manual_int")
    def _check_values(self):
        for line in self:
            if line.value_manual_int < 0:
                raise UserError(
                    _("The value of line '%s' (%d) is negative.")
                    % (line.box_id.display_name, line.value_manual_int)
                )
            if line.box_id.edi_type == "PCD" and line.value_manual_int > 100:
                raise UserError(
                    _("The value of line '%s' (%d) is over 100.")
                    % (line.box_id.display_name, line.value_manual_int)
                )

    @api.depends(
        "log_ids",
        "log_ids.amount",
        "value_bool",
        "value_manual_int",
        "box_id",
        "negative_switch",
    )
    def _compute_value(self):
        rg_res = self.env["l10n.fr.account.vat.return.line.log"].read_group(
            [("parent_id", "in", self.ids)], ["parent_id", "amount"], ["parent_id"]
        )
        mapped_data = {x["parent_id"][0]: x["amount"] for x in rg_res}
        for line in self:
            value = 0
            value_float = 0
            sign = line.negative_switch and -1 or 1
            if not line.box_id.display_type:
                if line.box_id.edi_type in ("MOA", "QTY", "PCD"):
                    if line.box_id.box_type == "manual":
                        value = line.value_manual_int
                    else:
                        value_float = mapped_data.get(line.id, 0)
                        value = int(round(value_float))
                elif line.box_id.edi_type == "CCI_TBX":
                    value = int(line.value_bool)
            line.value = value * sign
            line.value_float = value_float * sign


class L10nFrAccountVatReturnLineLog(models.Model):
    _name = "l10n.fr.account.vat.return.line.log"
    _description = "Compute log of VAT Return Line for France (CA3 line)"
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
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        ondelete="restrict",
        readonly=True,
    )
    compute_type = fields.Selection(
        [
            ("period_balance", "Period Balance"),  # used for untaxed operations
            ("balance", "Ending Balance"),  # used for VAT boxes
            ("unpaid_vat_on_payment", "Unpaid VAT on Payment"),  # used for VAT boxes
            ("computed_base", "Computed Base"),  # used for base VAT boxes
            ("computed_vat_amount", "Computed VAT Amount"),
            ("rate", "VAT Amount / VAT Rate"),
            ("box", "Box Value"),  # used for sum boxes (totals)
            ("manual", "Manual"),  # used for credit VAT reimbursement line
        ],
        required=True,
        readonly=True,
    )
    amount = fields.Float(readonly=True)
    origin_move_id = fields.Many2one(
        "account.move", string="Source Invoice", readonly=True
    )
    note = fields.Char()

    @api.constrains("parent_id", "account_id")
    def _check_account_id(self):
        for log in self:
            if (
                log.parent_id
                and log.parent_id.box_accounting_method
                and not log.account_id
            ):
                raise ValidationError(
                    _(
                        "Error in the generation of the computation and "
                        "accounting details of box '%s': this box has an "
                        "accounting method but the account is not set."
                    )
                    % log.parent_id.box_id.display_name
                )
