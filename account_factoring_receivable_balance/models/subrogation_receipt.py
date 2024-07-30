# © 2022 David BEAL @ Akretion
# © 2022 Alexis DE LATTRE @ Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SubrogationReceipt(models.Model):
    _name = "subrogation.receipt"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _check_company_auto = True
    _rec_name = "factor_type"
    _order = "target_date DESC"
    _description = "Customer balance data for factoring"

    factor_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        domain="[('factor_type', '!=', False)," "('type', '=', 'bank')]",
        check_company=True,
        required=True,
    )
    factor_type = fields.Selection(related="factor_journal_id.factor_type", store=True)
    currency_id = fields.Many2one(related="factor_journal_id.currency_id", store=True)
    display_name = fields.Char(compute="_compute_display_name")
    date = fields.Date(
        string="Confirmed Date",
        readonly=True,
        tracking=True,
    )
    target_date = fields.Date(
        help="All account moves line dates are lower or equal to this date",
        required=True,
        tracking=True,
    )
    statement_date = fields.Date(
        help="Date of the last bank statement taken account in accounting"
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("posted", "Posted"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    expense_untaxed_amount = fields.Monetary(tracking=True, help="")
    expense_tax_amount = fields.Monetary(tracking=True, help="")
    holdback_amount = fields.Monetary(tracking=True, help="")
    balance = fields.Monetary(readonly=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda s: s._get_company_id(),
        readonly=True,
        required=True,
    )
    comment = fields.Text()
    line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="subrogation_id",
    )

    @api.constrains("factor_journal_id", "state", "company_id")
    def _check_draft_per_journal(self):
        for rec in self:
            count_drafts = self.search_count(
                [
                    ("factor_journal_id", "=", rec.factor_journal_id.id),
                    ("state", "=", "draft"),
                    ("company_id", "=", rec._get_company_id()),
                ]
            )
            if count_drafts > 1:
                raise UserError(
                    _(
                        "You already have a Draft Subrogation with "
                        "this journal and company."
                    )
                )

    @api.depends("factor_journal_id", "date")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "{} {} {}".format(
                rec.factor_type,
                rec.currency_id.name,
                rec.date or rec._fields["state"].selection[0][1],
            )

    @api.model
    def _get_domain_for_factor(self):
        journal = self.factor_journal_id
        factor_type = self.factor_type
        factor_journal = self.factor_journal_id
        currency = journal.currency_id
        bank_journal = self._get_bank_journal(factor_type, currency=currency)
        domain = [
            ("date", "<=", self.target_date),
            ("company_id", "=", self._get_company_id()),
            ("parent_state", "=", "posted"),
            self._get_customer_accounts(),
            ("full_reconcile_id", "=", False),
            ("subrogation_id", "=", False),
            (
                "partner_id.commercial_partner_id.factor_journal_id",
                "=",
                factor_journal.id,
            ),
            "|",
            ("move_id.partner_bank_id", "=", bank_journal.bank_account_id.id),
            ("move_id.partner_bank_id", "=", False),
        ]
        domain += [
            (
                "move_id.currency_id",
                "=",
                (
                    journal.currency_id
                    and journal.currency_id.id
                    or journal.company_id.currency_id.id
                ),
            )
        ]
        if factor_journal.factor_start_date:
            domain.append(("date", ">=", factor_journal.factor_start_date))
        invoice_journals = self.factor_journal_id.factor_invoice_journal_ids
        if invoice_journals:
            domain.append(("journal_id", "in", invoice_journals.ids))
        return domain

    @api.model
    def _get_customer_accounts(self):
        return ("account_id.account_type", "=", "asset_receivable")

    def _get_factor_lines(self):
        domain = self._get_domain_for_factor()
        lines = self.env["account.move.line"].search(domain)
        return lines

    def action_compute_lines(self):
        self.ensure_one()
        self.line_ids.write({"subrogation_id": False})
        if not self.statement_date:
            statement = self.env["account.bank.statement"].search(
                [
                    ("journal_id.factor_type", "=", self.factor_type),
                    ("journal_id.currency_id", "=", self.currency_id.id),
                ],
                limit=1,
                order="date DESC",
            )
            if statement:
                self.statement_date = statement.date
        lines = self._get_factor_lines()
        lines.write({"subrogation_id": self.id})
        if self.line_ids:
            self.balance = sum(self.line_ids.mapped("amount_currency"))
        return True

    def _get_bank_journal(self, factor_type, currency=None):
        """Get matching bank journal
        You may override to have a dedicated mapping"""
        factor_type = self.factor_type
        currency = self.factor_journal_id.currency_id
        domain = [("type", "=", "bank"), ("factor_type", "=", factor_type)]
        if currency:
            domain += [("currency_id", "=", currency.id)]
        res = self.env["account.journal"].search(domain, limit=1)
        if not res:
            raise UserError(
                _("Missing bank journal with factor '%(ft)s' currency %(curr)s")
                % {"ft": factor_type, "curr": currency and currency.name or ""}
            )
        return res

    def _prepare_factor_file(self, factor_type):
        self.ensure_one()
        method = "_prepare_factor_file_%s" % factor_type
        if hasattr(self, method):
            return getattr(self, method)()
        else:
            pass

    def _sanitize_filepath(self, string):
        "Helper to make safe filepath"
        for elm in ["/", " ", ":", "<", ">", "\\", "|", "?", "*"]:
            string = string.replace(elm, "_")
        return string

    def action_confirm(self):
        for rec in self:
            if rec.state == "draft":
                rec.state = "confirmed"
                rec.date = fields.Date.today()
                data = self._prepare_factor_file(rec.factor_type)
                if data:
                    attachment = self.env["ir.attachment"].create(data)
                    self.message_post(attachment_ids=attachment.ids)

    def action_post(self):
        for rec in self:
            if (
                rec.state == "confirmed"
                and rec.holdback_amount > 0
                and rec.expense_untaxed_amount > 0
                and rec.expense_tax_amount > 0
            ):
                rec.state = "posted"
            else:
                raise UserError(
                    _(
                        "Check fields 'Holdabck Amount', 'Untaxed Amount', "
                        "'Tax Amount', they should have a value"
                    )
                )

    def action_goto_moves(self):
        self.ensure_one()
        return {
            "name": _("Subrogation Receipt %s") % self.display_name,
            "res_model": "account.move.line",
            "view_mode": "tree,form",
            "domain": "[('subrogation_id', '=', %s)]" % self.id,
            "type": "ir.actions.act_window",
        }

    def unlink(self):
        for rec in self:
            if rec.state == "posted":
                raise UserError(_("Subrogations in Posted state can't be deleted"))
        return super().unlink()

    def _get_company_id(self):
        return self.env.company.id
