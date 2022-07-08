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
    _description = "Customer balance data for factoring"

    factor_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        domain="[('factor_type', '!=', False), ('type', '=', 'general')]",
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
    expense_untaxed_amount = fields.Float(tracking=True, help="")
    expense_tax_amount = fields.Float(tracking=True, help="")
    holdback_amount = fields.Float(tracking=True, help="")
    balance = fields.Monetary(currency_field="currency_id", readonly=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda s: s._get_company_id(),
        readonly=True,
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="subrogation_id",
        readonly=True,
    )

    @api.constrains("factor_journal_id", "state", "company_id")
    def _check_draft_per_journal(self):
        for rec in self:
            if (
                self.search_count(
                    [
                        ("factor_journal_id", "=", rec.factor_journal_id.id),
                        ("state", "=", "draft"),
                        ("company_id", "=", rec._get_company_id()),
                    ]
                )
                > 1
            ):
                raise UserError(
                    _(
                        "You already have a Draft Subrogation with "
                        "this journal and company."
                    )
                )

    @api.depends("factor_journal_id", "date")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "%s %s %s" % (
                rec.factor_type,
                rec.currency_id.name,
                rec.date or rec._fields["state"].selection[0][1],
            )

    @api.model
    def _get_domain_for_factor(
        self, factor_type, partner_selection_field=None, currency=None
    ):
        """partner_selection_field is a field on partners to guess
        which account data need to be retrieved.
        You have to create it in your own fatcor module
        """
        bank_journal = self._get_bank_journal(factor_type, currency=currency)
        domain = [
            ("date", "<=", self.target_date),
            ("company_id", "=", self._get_company_id()),
            ("parent_state", "=", "posted"),
            ("subrogation_id", "=", False),
            self._get_customer_accounts(),
            ("full_reconcile_id", "=", False),
            (
                "partner_id.commercial_partner_id.%s" % partner_selection_field,
                "=",
                True,
            ),
            "|",
            ("move_id.partner_bank_id", "=", bank_journal.bank_account_id.id),
            ("move_id.partner_bank_id", "=", False),
        ]
        return domain

    @api.model
    def _get_customer_accounts(self):
        """We may also us:
        res = self.env["res.partner"].default_get(['property_account_receivable_id'])
        self.env["account.account"].browse(res["property_account_receivable_id"])

        but we are not sure that the user default one is the same
        """
        property_ = self.env["ir.property"].search(
            [
                ("name", "=", "property_account_receivable_id"),
                ("company_id", "=", self._get_company_id()),
                ("res_id", "=", False),
            ]
        )
        id_ = property_.value_reference[property_.value_reference.find(",") + 1 :]
        account = self.env["account.account"].browse(int(id_))
        return (
            "account_id.code",
            "like",
            "%s%s" % (account.code.replace("0", ""), "%"),
        )

    def _get_partner_field(self):
        "Inherit to define your own fields depending of your factor module"
        self.ensure_one()
        return None

    def action_compute_lines(self):
        self.ensure_one()
        journal = self.factor_journal_id
        domain = self._get_domain_for_factor(
            self.factor_type,
            partner_selection_field=self._get_partner_field(),
            currency=journal.currency_id,
        )
        self.line_ids.write({"subrogation_id": False})
        lines = self.env["account.move.line"].search(
            domain + [("move_id.currency_id", "=", journal.currency_id.id)]
        )
        lines.write({"subrogation_id": self.id})

    def _get_bank_journal(self, factor_type, currency=None):
        """Get matching bank journal
        You may override to have a dedicated mapping"""
        domain = [("type", "=", "bank"), ("factor_type", "=", factor_type)]
        if currency:
            domain += [("currency_id", "=", currency.id)]
        res = self.env["account.journal"].search(domain, limit=1)
        if not res:
            raise UserError(
                "Missing bank journal with factor '%s' currency %s"
                % (factor_type, currency and currency.name or "")
            )
        return res

    def _prepare_factor_file(self, factor_type):
        self.ensure_one
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
                    self.env["ir.attachment"].create(data)

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
            "name": _("Subrogation Receipt %s" % self.display_name),
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
        return self.env.user.company_id.id
