# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
from odoo.tools.misc import format_date

logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    fr_vat_periodicity = fields.Selection(
        [
            ("1", "Monthly"),
            ("3", "Quarterly"),
            ("12", "Yearly"),
        ],
        default="1",
        string="VAT Periodicity",
    )
    fr_vat_exigibility = fields.Selection(
        "_fr_vat_exigibility_selection",
        default="on_invoice",
        string="VAT Exigibility",
    )
    fr_vat_update_lock_dates = fields.Boolean(
        string="Update Lock Date upon VAT Return Validation"
    )
    fr_vat_journal_id = fields.Many2one(
        "account.journal",
        string="Journal for VAT Journal Entry",
        ondelete="restrict",
        check_company=True,
    )
    # Field names from l10n_fr_account v18
    l10n_fr_rounding_difference_loss_account_id = fields.Many2one(
        "account.account",
        check_company=True,
        string="Expense Account for Rounding",
    )
    l10n_fr_rounding_difference_profit_account_id = fields.Many2one(
        "account.account", check_company=True, string="Income Account for Rounding"
    )
    fr_vat_expense_analytic_distribution = fields.Json(
        string="Analytic Expense Account for Rounding",
        compute="_compute_fr_vat_analytic_distribution",
        store=True,
        readonly=False,
    )
    fr_vat_income_analytic_distribution = fields.Json(
        string="Analytic Income Account for Rounding",
        compute="_compute_fr_vat_analytic_distribution",
        store=True,
        readonly=False,
    )
    analytic_precision = fields.Integer(
        default=lambda self: self.env["decimal.precision"].precision_get(
            "Percentage Analytic"
        ),
    )
    fr_vat_manual_autoliq_line_default_option = fields.Selection(
        [
            ("product", "Product"),
            ("service", "Service"),
        ],
        string="Default for Manual Autoliquidation Line",
    )
    fr_vat_bank_account_id = fields.Many2one(
        "res.partner.bank",
        string="Company Bank Account",
        check_company=True,
        ondelete="restrict",
        help="Company bank account used to pay VAT or receive credit VAT reimbursements.",
    )
    fr_vat_send_gateway = fields.Selection(
        "_fr_vat_send_gateway_selection", string="Default VAT Gateway"
    )
    fr_vat_remind_user_ids = fields.Many2many(
        "res.users",
        "fr_vat_company_remind_user_rel",
        "company_id",
        "user_id",
        string="Users to Remind",
    )
    fr_vat_remind_deadline_day = fields.Selection(
        [
            ("15", "15"),
            ("16", "16"),
            ("17", "17"),
            ("18", "18"),
            ("19", "19"),
            ("20", "20"),
            ("21", "21"),
            ("22", "22"),
            ("23", "23"),
            ("24", "24"),
        ],
        string="VAT Return Deadline Day",
        default="20",
    )
    fr_vat_remind_auto_generate_and_transmit = fields.Boolean(
        string="Auto-generate and Transmit on Deadline Day"
    )

    @api.model
    def _fr_vat_exigibility_selection(self):
        res = [
            ("on_invoice", _("Based on invoice")),
            ("on_payment", _("Based on payment")),
            ("auto", _("Both (automatic)")),
        ]
        return res

    @api.model
    def _fr_vat_send_gateway_selection(self):
        return self.env["l10n.fr.account.vat.return"]._send_gateway_selection()

    @api.constrains(
        "fr_vat_manual_autoliq_line_default_option",
        "fr_vat_remind_auto_generate_and_transmit",
    )
    def _check_vat_fr(self):
        for company in self:
            if (
                company.fr_vat_remind_auto_generate_and_transmit
                and not company.fr_vat_manual_autoliq_line_default_option
            ):
                raise ValidationError(
                    _(
                        "As the option 'Auto-generate and Transmit on Deadline Day' "
                        "is enabled on company %s, you must configure the option "
                        "'Default for Manual Autoliquidation Line'.",
                        company.display_name,
                    )
                )

    def _compute_fr_vat_analytic_distribution(self):
        aadmo = self.env["account.analytic.distribution.model"]
        for company in self:
            expense_distri = aadmo._get_distribution(
                {
                    "account_prefix": "658",
                    "company_id": company.id,
                }
            )
            income_distri = aadmo._get_distribution(
                {
                    "account_prefix": "758",
                    "company_id": company.id,
                }
            )
            company.fr_vat_expense_analytic_distribution = expense_distri
            company.fr_vat_income_analytic_distribution = income_distri

    def _fr_vat_remind_auto_generate_and_transmit(
        self, vat_return, last_start_date, msg_list
    ):
        self.ensure_one()
        if vat_return:
            assert vat_return.state in ("manual", "auto")
            msg_list.append(
                _(
                    "Existing VAT return %s found.",
                    vat_return.display_name,
                )
            )
        else:
            msg_list.append(
                _(
                    "Trying to create a new VAT return with start date %s...",
                    format_date(self.env, last_start_date),
                )
            )
            vat_return = self.env["l10n.fr.account.vat.return"].create(
                {
                    "company_id": self.id,
                    "start_date": last_start_date,
                    "ignore_draft_moves": True,
                }
            )
            msg_list.pop()
            msg_list.append(
                _("VAT return %s successfully generated.", vat_return.display_name)
            )
            vat_return.message_post(
                body=_(
                    "This VAT return has been auto-generated by the scheduled action."
                )
            )
        if vat_return.state == "manual":
            msg_list.append(_("Trying to generate the automatic lines..."))
            wvals = {}
            if not vat_return.ignore_draft_moves:
                wvals["ignore_draft_moves"] = True
            if wvals:
                vat_return.write(wvals)
            vat_return.with_context(
                fr_vat_remind_auto_generate_and_transmit=True
            ).manual2auto()
            msg_list.pop()
            msg_list.append(_("The automatic lines have been successfully generated."))
            vat_return.message_post(
                body=_(
                    "Automatic lines have been automatically generated by the scheduled action."
                )
            )
        assert vat_return.state == "auto"
        msg_list.append(_("Trying to send the VAT return via the gateway..."))
        vat_return.auto2sent_via_gateway()
        msg_list.pop()
        msg_list.append(_("The VAT return has been successfully sent via the gateway."))
        vat_return.message_post(
            body=_(
                "VAT return automatically sent via the gateway by the scheduled action."
            )
        )
        return True  # designed to materialize the success

    @api.model
    def _fr_vat_cron_mail_remind_and_auto_generate_transmit(self):
        logger.info("Start cron FR VAT return reminder and auto-generate/transmit")
        today = fields.Date.context_today(self)
        # for TEST/debug
        # today = datetime.strptime("2026-01-20", "%Y-%m-%d")
        mail_tpl = self.env.ref(
            "l10n_fr_account_vat_return.fr_vat_return_remind_mail_template"
        )
        companies = self.sudo().search(
            [
                ("fr_vat_periodicity", "in", ("1", "3")),
                ("fr_vat_remind_deadline_day", "!=", False),
            ]
        )
        for company in companies:
            deadline_day = int(company.fr_vat_remind_deadline_day)
            delta_days = deadline_day - today.day
            logger.debug(
                "Company %s: deadline_day=%s delta_days=%s",
                company.display_name,
                deadline_day,
                delta_days,
            )
            if delta_days < 0 or delta_days > 3:
                continue
            if company.fr_vat_periodicity == "1":
                last_start_date = today + relativedelta(months=-1, day=1)
            elif company.fr_vat_periodicity == "3":
                if today.month in (1, 4, 7, 10):
                    last_start_date = today + relativedelta(months=-3, day=1)
                else:
                    logger.info(
                        "Skip company %s because its VAT periodicity is quarterly "
                        "and there is no declaration this month",
                        company.display_name,
                    )
                    continue
            vat_return = self.env["l10n.fr.account.vat.return"].search(
                [
                    ("company_id", "=", company.id),
                    ("start_date", "=", last_start_date),
                ],
                limit=1,
            )
            if vat_return.state in ("sent", "posted"):
                logger.info(
                    "No reminder for company %s because its VAT return %s "
                    "has already been sent",
                    company.display_name,
                    vat_return.display_name,
                )
                continue

            transmit_ok = False
            msg_list = []
            if not delta_days and company.fr_vat_remind_auto_generate_and_transmit:
                if vat_return:
                    logger.info(
                        "Trying to send automatically the existing VAT return %s "
                        "state %s of company %s",
                        vat_return.display_name,
                        vat_return.state,
                        company.display_name,
                    )
                else:
                    logger.info(
                        "Trying to auto-generate and send the VAT return of "
                        "company %s with last_start_date=%s",
                        company.display_name,
                        last_start_date,
                    )
                try:
                    transmit_ok = company._fr_vat_remind_auto_generate_and_transmit(
                        vat_return, last_start_date, msg_list
                    )
                except Exception as err:
                    msg_list.append(_("Odoo raised an error, see detailed below."))
                    msg_list.append(str(err))
                    logger.warning(str(err))
            if company.fr_vat_remind_user_ids:
                logger.info(
                    "Generating reminder email for company %s", company.display_name
                )
                mail_tpl.with_context(
                    delta_days=delta_days, msg_list=msg_list, transmit_ok=transmit_ok
                ).send_mail(company.id)
            else:
                logger.info(
                    "No FR VAT mail reminder generated in company %s because "
                    "there are no users to remind configured in that company",
                    company.display_name,
                )

        logger.info("End of cron FR VAT return reminder and auto-generate/transmit")

    @api.model
    def _fr_vat_init_adjustment_accounts_all_companies(self):
        logger.info("Launching FR VAT setup script on all FR companies")
        companies = self.search(
            [
                (
                    "account_fiscal_country_id.code",
                    "in",
                    ("FR", "GP", "MQ", "GF", "RE", "YT"),
                ),
                ("l10n_fr_rounding_difference_loss_account_id", "=", False),
                ("l10n_fr_rounding_difference_profit_account_id", "=", False),
            ]
        )
        for company in companies:
            company._fr_vat_init_adjustment_accounts()

    def _fr_vat_init_adjustment_accounts(self):
        self.ensure_one()
        logger.info(
            "Configuring FR VAT adjust accounts on company %s", self.display_name
        )
        vals = {}
        exp_account = self.env["account.account"].search(
            [
                ("company_id", "=", self.id),
                ("code", "=like", "658%"),
                ("account_type", "=", "expense"),
            ],
            limit=1,
        )
        if exp_account:
            vals["l10n_fr_rounding_difference_loss_account_id"] = exp_account.id
        inc_account = self.env["account.account"].search(
            [
                ("company_id", "=", self.id),
                ("code", "=like", "758%"),
                ("account_type", "=", "income"),
            ],
            limit=1,
        )
        if inc_account:
            vals["l10n_fr_rounding_difference_profit_account_id"] = inc_account.id
        if vals:
            self.write(vals)

    @api.model
    def _test_fr_vat_create_company(
        self, company_name=None, fr_vat_exigibility="on_invoice"
    ):
        # I write this method here and not in the test,
        # because it can be very useful for demos too
        self = self.sudo()
        company_vals = {
            "name": company_name or "FR Company VAT",
            "fr_vat_exigibility": fr_vat_exigibility,
            "street": "42 rue du logiciel libre",
            "zip": "69009",
            "city": "Lyon",
            "country_id": self.env.ref("base.fr").id,
            "siret": "77788899100018",
            "vat": "FR51777888991",
        }
        if hasattr(self, "siren"):
            company_vals.update(
                {
                    "siren": company_vals["siret"][:9],
                    "nic": company_vals["siret"][9:],
                }
            )
            company_vals.pop("siret")
        company = self.create(company_vals)
        logger.info("Company %s created", company.display_name)
        self.env.user.write({"company_ids": [Command.link(company.id)]})
        logger.info(
            "Loading fr_oca chart of account on company %s", company.display_name
        )
        fr_chart_template = self.env.ref("l10n_fr_oca.l10n_fr_pcg_chart_template")
        fr_chart_template._load(company)
        bank = self.env["res.bank"].create(
            {
                "name": "Qonto",
                "bic": "QNTOFRP1XXX",
            }
        )
        self.env["res.partner.bank"].create(
            {
                "acc_number": "FR4712122323343445455656676",
                "partner_id": company.partner_id.id,
                "company_id": company.id,
                "bank_id": bank.id,
            }
        )
        company._setup_l10n_fr_coa_vat_company()
        return company

    def _setup_l10n_fr_coa_vat_company(self):  # noqa: C901
        self.ensure_one()
        afpo = self.env["account.fiscal.position"]
        afpao = self.env["account.fiscal.position.account"]
        afpto = self.env["account.fiscal.position.tax"]
        aao = self.env["account.account"]
        ato = self.env["account.tax"]
        cdomain = [("company_id", "=", self.id)]
        od_journal = self.env["account.journal"].search(
            cdomain + [("type", "=", "general")], limit=1
        )
        self.tax_cash_basis_journal_id.unlink()
        self.write(
            {
                "fr_vat_journal_id": od_journal.id,
                "fr_vat_bank_account_id": self.partner_id.bank_ids[0].id,
            }
        )
        # Set 658/758 accounts
        self._fr_vat_init_adjustment_accounts()
        # activate all taxes
        ato.search(cdomain + [("active", "=", False)]).write({"active": True})
        # France autoliq taxes for BTP subcontracting
        btp_account_map = {
            "445401": "TVA due sur achats sous-traitance BTP 20% (autoliquidation)",
            "445402": "TVA due sur achats sous-traitance BTP 10% (autoliquidation)",
            "445403": "TVA due sur achats sous-traitance BTP 5,5% (autoliquidation)",
            "445664": "TVA déductible autoliquidation sous-traitance BTP",
        }
        btp_account2id = {}
        for code, name in btp_account_map.items():
            account_type = code == "445664" and "asset_current" or "liability_current"
            btp_account2id[code] = aao.create(
                {
                    "name": name,
                    "company_id": self.id,
                    "code": code,
                    "account_type": account_type,
                    "reconcile": True,
                }
            ).id
        btp_tax2id = {}
        btp_tax_map = {
            200: "445401",
            100: "445402",
            55: "445403",
        }
        for rate_int, account_code in btp_tax_map.items():
            rate = rate_int / 10
            if rate == int(rate):
                rate = int(rate)
            repartition_line_ids = [
                Command.create(
                    {
                        "repartition_type": "base",
                    }
                ),
                Command.create(
                    {
                        "factor_percent": 100,
                        "repartition_type": "tax",
                        "account_id": btp_account2id["445664"],
                    }
                ),
                Command.create(
                    {
                        "factor_percent": -100,
                        "repartition_type": "tax",
                        "account_id": btp_account2id[account_code],
                    }
                ),
            ]
            btp_tax2id[rate_int] = ato.create(
                {
                    "type_tax_use": "purchase",
                    "name": f"TVA sous-traitance BTP {rate}%",
                    "company_id": self.id,
                    "amount_type": "percent",
                    "amount": rate,
                    "description": f"TVA {rate}% france autoliq",
                    "country_id": self.env.ref("base.fr").id,
                    "unece_type_id": self.env.ref("account_tax_unece.tax_type_vat").id,
                    "invoice_repartition_line_ids": repartition_line_ids,
                    "refund_repartition_line_ids": repartition_line_ids,
                }
            ).id
        # Create France exo FP
        france_exo_fp = afpo.create(
            {
                "name": "France sous-traitance BTP",
                "fr_vat_type": "france_exo",
                "auto_apply": False,
                "company_id": self.id,
            }
        )
        exo_fp_account_map = {
            "701100": "701500",
            "706100": "706500",
            "707100": "707500",
            "708510": "708550",
        }
        for src_acc_code, dest_acc_code in exo_fp_account_map.items():
            src_account = aao.search(cdomain + [("code", "=", src_acc_code)], limit=1)
            assert src_account
            dest_account = aao.create(
                {
                    "company_id": self.id,
                    "code": dest_acc_code,
                    "name": f"{src_account.name} exonéré",
                    "account_type": "income",
                    "reconcile": False,
                    "tax_ids": False,
                }
            )
            afpao.create(
                {
                    "position_id": france_exo_fp.id,
                    "account_src_id": src_account.id,
                    "account_dest_id": dest_account.id,
                }
            )
        # I use extracom FP to get the list of source taxes
        extracom_fp = afpo.search(cdomain + [("fr_vat_type", "=", "extracom")], limit=1)
        sale_tax_dest_id = self.env.ref(f"l10n_fr_oca.{self.id}_tva_sale_0_exo").id

        for extracom_tax_line in extracom_fp.tax_ids:
            if extracom_tax_line.tax_src_id.type_tax_use == "sale":
                tax_dest_id = sale_tax_dest_id
            else:
                if extracom_tax_line.tax_src_id.amount < 5:  # skip 2.1%
                    continue
                tax_dest_id = btp_tax2id[int(extracom_tax_line.tax_src_id.amount * 10)]
            afpto.create(
                {
                    "position_id": france_exo_fp.id,
                    "tax_src_id": extracom_tax_line.tax_src_id.id,
                    "tax_dest_id": tax_dest_id,
                }
            )
        # Update account mapping on IntraEU B2B and Export
        # for the very specific scenario of untaxed products
        fp_to_update = {
            "extracom": {
                "701500": "701400",
                "706500": "706400",
                "707500": "707400",
                "708550": "708540",
            },
            "intracom_b2b": {
                "701500": "701200",
                "706500": "706200",
                "707500": "707200",
                "708550": "708520",
            },
        }
        for fp_fr_vat_type, fp_account_map in fp_to_update.items():
            fp = afpo.search(cdomain + [("fr_vat_type", "=", fp_fr_vat_type)], limit=1)
            for src_acc_code, dest_acc_code in fp_account_map.items():
                src_acc = aao.search(cdomain + [("code", "=", src_acc_code)])
                dest_acc = aao.search(cdomain + [("code", "=", dest_acc_code)])
                afpao.create(
                    {
                        "position_id": fp.id,
                        "account_src_id": src_acc.id,
                        "account_dest_id": dest_acc.id,
                    }
                )
        self._setup_l10n_fr_create_royalty_purchase_tax()

    def _setup_l10n_fr_create_royalty_purchase_tax(self):
        due_vat_account = self.env["account.account"].create(
            {
                "name": "TVA collectée droits d'auteur 9,2%",
                "company_id": self.id,
                "code": "445719",
                "account_type": "liability_current",
                "reconcile": True,
            }
        )
        deduc_vat_account = self.env["account.account"].create(
            {
                "name": "TVA déductible droits d'auteur 10%",
                "company_id": self.id,
                "code": "445669",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        repartition_line_ids = [
            Command.create(
                {
                    "repartition_type": "base",
                }
            ),
            Command.create(
                {
                    "factor_percent": 100,
                    "repartition_type": "tax",
                    "account_id": deduc_vat_account.id,
                }
            ),
            Command.create(
                {
                    "factor_percent": -92,
                    "repartition_type": "tax",
                    "account_id": due_vat_account.id,
                }
            ),
        ]
        royalty_tax = self.env["account.tax"].create(
            {
                "type_tax_use": "purchase",
                "name": "TVA droits d'auteur",
                "company_id": self.id,
                "amount_type": "percent",
                "amount": 10,
                "description": "TVA droits d'auteur",
                "country_id": self.env.ref("base.fr").id,
                "unece_type_id": self.env.ref("account_tax_unece.tax_type_vat").id,
                "invoice_repartition_line_ids": repartition_line_ids,
                "refund_repartition_line_ids": repartition_line_ids,
            }
        )
        assert royalty_tax.fr_vat_autoliquidation == "partial"

    def _test_create_invoice_with_payment(
        self, move_type, date, partner, lines, payments, force_in_vat_on_payment=False
    ):
        self.ensure_one()
        amo = self.env["account.move"].with_company(self.id)
        apro = self.env["account.payment.register"]
        vals = {
            "company_id": self.id,
            "move_type": move_type,
            "invoice_date": date,
            "partner_id": partner.id,
            "currency_id": self.currency_id.id,
            "invoice_line_ids": [],
        }
        for line in lines:
            if "quantity" not in line:
                line["quantity"] = 1
            line["display_type"] = "product"
            vals["invoice_line_ids"].append(Command.create(line))
        if move_type == "in_invoice":
            vals["ref"] = f"FAC{datetime.now().strftime('%f')}"
        elif move_type == "in_refund":
            vals["ref"] = f"AV{datetime.now().strftime('%f')}"
        move = amo.create(vals)
        if move_type in ("in_invoice", "in_refund") and force_in_vat_on_payment:
            move.write({"in_vat_on_payment": True})
        move.action_post()

        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", self.id)], limit=1
        )
        assert bank_journal
        for pay_date, payment_ratio in payments.items():
            vals = {
                "journal_id": bank_journal.id,
                "payment_date": pay_date,
            }
            if payment_ratio != "residual":
                assert payment_ratio > 0 and payment_ratio < 100
                vals["amount"] = self.currency_id.round(
                    move.amount_total * payment_ratio / 100
                )
            payment_wiz = apro.with_context(
                active_model="account.move", active_ids=[move.id]
            ).create(vals)
            payment_wiz.action_create_payments()
        return move

    def _test_get_account(self, code):
        self.ensure_one()
        account = self.env["account.account"].search(
            [
                ("code", "=", code),
                ("company_id", "=", self.id),
            ],
            limit=1,
        )
        assert account
        return account

    def _test_get_tax(self, type_tax_use, vat_rate, asset=False):
        self.ensure_one()
        taxes = (
            self.env["account.tax"]
            .with_context(active_test=False)
            .search(
                [
                    ("company_id", "=", self.id),
                    ("type_tax_use", "=", type_tax_use),
                    ("amount_type", "=", "percent"),
                    ("price_include", "=", False),
                    ("fr_vat_autoliquidation", "=", False),
                ]
            )
        )
        for tax in taxes:
            if not asset and "immo" in tax.name:
                continue
            if asset and "immo" not in tax.name:
                continue
            if not float_compare(vat_rate, tax.amount, precision_digits=4):
                return tax
        return False

    def _test_common_product_dict(
        self, product_dict, asset=False, product_type="consu"
    ):
        ppo = self.env["product.product"].with_company(self.id)
        for vat_rate in product_dict.keys():
            if vat_rate == 21 and asset:
                continue
            if vat_rate:
                real_vat_rate = vat_rate / 10
                sale_tax = self._test_get_tax("sale", real_vat_rate)
                assert sale_tax
                sale_tax_ids = [Command.set([sale_tax.id])]
                purchase_tax = self._test_get_tax(
                    "purchase", real_vat_rate, asset=asset
                )
                assert purchase_tax
                purchase_tax_ids = [Command.set([purchase_tax.id])]
                account_income_id = False
            else:
                real_vat_rate = 0
                exo_tax_xmlid = "l10n_fr_oca.%d_tva_%s_0_exo"
                sale_tax = self.env.ref(exo_tax_xmlid % (self.id, "sale"))
                sale_tax_ids = [Command.set([sale_tax.id])]
                purchase_tax = self.env.ref(exo_tax_xmlid % (self.id, "purchase"))
                purchase_tax_ids = [Command.set([purchase_tax.id])]
                account_income_id = self._test_get_account("707500").id
            product_name = (
                f"Test-demo {product_type} TVA {real_vat_rate}%"
                f"{asset and ' immo' or ''}"
            )
            pvals = {
                "name": product_name,
                "type": product_type,
                "sale_ok": True,
                "purchase_ok": True,
                "taxes_id": sale_tax_ids,
                "supplier_taxes_id": purchase_tax_ids,
                "categ_id": self.env.ref("product.product_category_all").id,
                "property_account_income_id": account_income_id,
                "company_id": self.id,
            }
            product = ppo.create(pvals)
            product_dict[vat_rate] = product

    def _test_prepare_product_dict(self):
        rate2product = {
            200: False,
            100: False,
            55: False,
            21: False,
            0: False,
        }

        product_dict = {
            "product": dict(rate2product),
            "service": dict(rate2product),
            "asset": dict(rate2product),
            "royalty": dict(rate2product),
        }
        self._test_common_product_dict(product_dict["product"])
        self._test_common_product_dict(product_dict["asset"], asset=True)
        self._test_common_product_dict(product_dict["service"], product_type="service")
        royalty_tax = self.env["account.tax"].search(
            [
                ("company_id", "=", self.id),
                ("amount_type", "=", "percent"),
                ("amount", ">", 9.99),
                ("amount", "<", 10.01),
                ("unece_type_code", "=", "VAT"),
                ("country_id", "=", self.env.ref("base.fr").id),
                ("fr_vat_autoliquidation", "=", "partial"),
            ]
        )
        assert len(royalty_tax) == 1
        royalty_product = self.env["product.product"].create(
            {
                "name": "Droits d'auteur",
                "type": "service",
                "sale_ok": False,
                "purchase_ok": True,
                "supplier_taxes_id": [Command.set([royalty_tax.id])],
                "categ_id": self.env.ref("product.product_category_all").id,
                "company_id": self.id,
            }
        )
        product_dict["royalty"][100] = royalty_product
        return product_dict

    def _test_prepare_expense_account_dict(self):
        aao = self.env["account.account"]
        account_dict = {
            "service": "6226",
            "product": "607",
        }
        for key, account_prefix in account_dict.items():
            account = aao.search(
                [
                    ("code", "=ilike", account_prefix + "%"),
                    ("company_id", "=", self.id),
                ],
                limit=1,
            )
            assert account
            account_dict[key] = account
        return account_dict

    def _test_prepare_partner_dict(self):
        self.ensure_one()
        partner_dict = {
            "france": False,
            "france_vendor_vat_on_payment": False,
            "intracom_b2b": self.env.ref("intrastat_base.forgeflow"),
            #  "intracom_b2c": False,
            "extracom": False,
            "france_exo": False,
        }
        afpo = self.env["account.fiscal.position"]
        rpo = self.env["res.partner"].with_company(self.id)
        for fr_vat_type, partner in partner_dict.items():
            fiscal_position = afpo.search(
                [("company_id", "=", self.id), ("fr_vat_type", "=", fr_vat_type)],
                limit=1,
            )
            assert fiscal_position
            if partner:
                partner.with_company(self.id).write(
                    {"property_account_position_id": fiscal_position.id}
                )
            else:
                partner = rpo.create(
                    {
                        "is_company": True,
                        "name": f"Test-demo {fr_vat_type}",
                        "property_account_position_id": fiscal_position.id,
                        "company_id": self.id,
                    }
                )
                partner_dict[fr_vat_type] = partner
        france_fiscal_position = afpo.search(
            [("company_id", "=", self.id), ("fr_vat_type", "=", "france")], limit=1
        )
        partner_dict["monaco"] = rpo.create(
            {
                "name": "Monaco Partner",
                "is_company": True,
                "company_id": self.id,
                "country_id": self.env.ref("base.mc").id,
                "property_account_position_id": france_fiscal_position.id,
            }
        )
        partner_dict["france_royalty"] = rpo.create(
            {
                "name": "Auteur Artiste",
                "is_company": True,
                "company_id": self.id,
                "country_id": self.env.ref("base.fr").id,
                "property_account_position_id": france_fiscal_position.id,
            }
        )
        return partner_dict

    def _test_create_move_init_vat_credit(self, amount, start_date):
        self.ensure_one()
        credit_acc = self._test_get_account("445670")
        wait_acc = self._test_get_account("471000")
        date = start_date + relativedelta(months=-3)
        move = self.env["account.move"].create(
            {
                "company_id": self.id,
                "date": date,
                "journal_id": self.fr_vat_journal_id.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": credit_acc.id,
                            "debit": amount,
                        },
                    ),
                    Command.create(
                        {
                            "account_id": wait_acc.id,
                            "credit": amount,
                        },
                    ),
                ],
            }
        )
        move.action_post()

    def _test_create_invoice_data(
        self, start_date, extracom_refund_ratio=0.5, with_royalty=True
    ):
        product_dict = self._test_prepare_product_dict()
        partner_dict = self._test_prepare_partner_dict()
        account_dict = self._test_prepare_expense_account_dict()
        after_end_date = start_date + relativedelta(months=1)
        mid_date = start_date + relativedelta(days=12)
        # OUT INVOICE/REFUND
        # regular unpaid
        self._test_create_invoice_with_payment(
            "out_invoice",
            start_date,
            partner_dict["france"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 10},
                {"product_id": product_dict["product"][100].id, "price_unit": 20},
                {"product_id": product_dict["product"][55].id, "price_unit": 1000},
                {"product_id": product_dict["product"][21].id, "price_unit": 2000},
                {"product_id": product_dict["product"][0].id, "price_unit": 100},
            ],
            {},
        )
        # regular partially paid before end date
        self._test_create_invoice_with_payment(
            "out_invoice",
            start_date,
            partner_dict["france"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 30},
                {"product_id": product_dict["product"][100].id, "price_unit": 40},
                {"product_id": product_dict["product"][55].id, "price_unit": 3000},
                {"product_id": product_dict["product"][21].id, "price_unit": 4000},
                {"product_id": product_dict["product"][0].id, "price_unit": 200},
            ],
            {start_date: 25},
        )
        # regular partially paid after end date
        self._test_create_invoice_with_payment(
            "out_invoice",
            start_date,
            partner_dict["france"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 50},
                {"product_id": product_dict["product"][100].id, "price_unit": 60},
                {"product_id": product_dict["product"][55].id, "price_unit": 5000},
                {"product_id": product_dict["product"][21].id, "price_unit": 6000},
                {"product_id": product_dict["product"][0].id, "price_unit": 300},
            ],
            {after_end_date: 40},
        )
        # regular paid before end date
        self._test_create_invoice_with_payment(
            "out_invoice",
            start_date,
            partner_dict["france"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 70},
                {"product_id": product_dict["product"][100].id, "price_unit": 80},
                {"product_id": product_dict["product"][55].id, "price_unit": 7000},
                {"product_id": product_dict["product"][21].id, "price_unit": 8000},
                {"product_id": product_dict["product"][0].id, "price_unit": 400},
            ],
            {mid_date: "residual"},
        )
        # regular paid after end date
        self._test_create_invoice_with_payment(
            "out_invoice",
            start_date,
            partner_dict["france"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 90},
                {"product_id": product_dict["product"][100].id, "price_unit": 100},
                {"product_id": product_dict["product"][55].id, "price_unit": 9000},
                {"product_id": product_dict["product"][21].id, "price_unit": 10000},
                {"product_id": product_dict["product"][0].id, "price_unit": 500},
            ],
            {after_end_date: "residual"},
        )
        # monaco
        self._test_create_invoice_with_payment(
            "out_invoice",
            start_date,
            partner_dict["monaco"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 110},
                {"product_id": product_dict["product"][100].id, "price_unit": 120},
                {"product_id": product_dict["product"][55].id, "price_unit": 11000},
                {"product_id": product_dict["product"][21].id, "price_unit": 12000},
                {"product_id": product_dict["product"][0].id, "price_unit": 600},
            ],
            {start_date: "residual"},
        )
        # refund unpaid
        self._test_create_invoice_with_payment(
            "out_refund",
            start_date,
            partner_dict["france"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 130},
                {"product_id": product_dict["product"][100].id, "price_unit": 140},
                {"product_id": product_dict["product"][55].id, "price_unit": 13000},
                {"product_id": product_dict["product"][21].id, "price_unit": 14000},
                {"product_id": product_dict["product"][0].id, "price_unit": 700},
            ],
            {},
        )
        # intracom B2B
        self._test_create_invoice_with_payment(
            "out_invoice",
            start_date,
            partner_dict["intracom_b2b"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 10},
                {"product_id": product_dict["product"][100].id, "price_unit": 20},
                {"product_id": product_dict["product"][55].id, "price_unit": 30},
                {"product_id": product_dict["product"][21].id, "price_unit": 40},
                {"product_id": product_dict["product"][0].id, "price_unit": 50},
            ],
            {start_date: "residual"},
        )
        # extracom invoice
        self._test_create_invoice_with_payment(
            "out_invoice",
            start_date,
            partner_dict["extracom"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 100},
                {"product_id": product_dict["product"][100].id, "price_unit": 200},
                {"product_id": product_dict["product"][55].id, "price_unit": 300},
                {"product_id": product_dict["product"][21].id, "price_unit": 400},
                {"product_id": product_dict["product"][0].id, "price_unit": 500},
            ],
            {start_date: "residual"},
        )
        # extracom refund
        ratio = extracom_refund_ratio
        self._test_create_invoice_with_payment(
            "out_refund",
            start_date,
            partner_dict["extracom"],
            [
                {
                    "product_id": product_dict["product"][200].id,
                    "price_unit": 100 * ratio,
                },
                {
                    "product_id": product_dict["product"][100].id,
                    "price_unit": 200 * ratio,
                },
                {
                    "product_id": product_dict["product"][55].id,
                    "price_unit": 300 * ratio,
                },
                {
                    "product_id": product_dict["product"][21].id,
                    "price_unit": 400 * ratio,
                },
                {
                    "product_id": product_dict["product"][0].id,
                    "price_unit": 500 * ratio,
                },
            ],
            {start_date: "residual"},
        )
        # IN INVOICE/PAYMENT
        self._test_create_invoice_with_payment(
            "in_invoice",
            start_date,
            partner_dict["france"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 110},
                {"product_id": product_dict["product"][100].id, "price_unit": 110},
                {"product_id": product_dict["product"][55].id, "price_unit": 110},
                {"product_id": product_dict["product"][21].id, "price_unit": 110},
            ],
            {start_date: "residual"},
        )
        self._test_create_invoice_with_payment(
            "in_refund",
            start_date,
            partner_dict["france"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 10},
                {"product_id": product_dict["product"][100].id, "price_unit": 10},
                {"product_id": product_dict["product"][55].id, "price_unit": 10},
                {"product_id": product_dict["product"][21].id, "price_unit": 10},
            ],
            {start_date: "residual"},
        )
        self._test_create_invoice_with_payment(
            "in_invoice",
            start_date,
            partner_dict["france"],
            [
                {"product_id": product_dict["asset"][200].id, "price_unit": 5000},
                {"product_id": product_dict["asset"][100].id, "price_unit": 100},
                {"product_id": product_dict["asset"][55].id, "price_unit": 1000},
            ],
            {start_date: "residual"},
        )
        self._test_create_invoice_with_payment(  # No impact
            "in_invoice",
            start_date,
            partner_dict["france_vendor_vat_on_payment"],
            [{"product_id": product_dict["asset"][200].id, "price_unit": 10000}],
            {},
        )
        self._test_create_invoice_with_payment(  # No impact
            "in_refund",
            start_date,
            partner_dict["france_vendor_vat_on_payment"],
            [{"product_id": product_dict["asset"][200].id, "price_unit": 1234}],
            {},
        )
        self._test_create_invoice_with_payment(  # No impact
            "in_invoice",
            start_date,
            partner_dict["france_vendor_vat_on_payment"],
            [{"product_id": product_dict["product"][200].id, "price_unit": 10000}],
            {after_end_date: "residual"},
        )
        # VAT on payment with partial payment
        # I don't put partial payment in asset supplier invoices in order
        # to allow 445620 to be reconciled and test that it works
        self._test_create_invoice_with_payment(  # No impact
            "in_invoice",
            start_date,
            partner_dict["france_vendor_vat_on_payment"],
            [{"product_id": product_dict["product"][200].id, "price_unit": 10000}],
            {after_end_date: 25},
        )
        self._test_create_invoice_with_payment(
            "in_invoice",
            start_date,
            partner_dict["france_vendor_vat_on_payment"],
            [{"product_id": product_dict["product"][200].id, "price_unit": 1000}],
            {start_date: 25},
        )
        self._test_create_invoice_with_payment(
            "in_invoice",
            start_date,
            partner_dict["france_vendor_vat_on_payment"],
            [{"product_id": product_dict["product"][100].id, "price_unit": 100}],
            {start_date: 70, after_end_date: "residual"},
        )
        # HA intracom
        self._test_create_invoice_with_payment(
            "in_invoice",
            start_date,
            partner_dict["intracom_b2b"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 75},
                {"product_id": product_dict["service"][200].id, "price_unit": 25},
                {"product_id": product_dict["product"][100].id, "price_unit": 80},
                {"product_id": product_dict["service"][100].id, "price_unit": 30},
                {"product_id": product_dict["product"][55].id, "price_unit": 750},
                {"product_id": product_dict["service"][55].id, "price_unit": 250},
                {"product_id": product_dict["product"][21].id, "price_unit": 300},
                {"product_id": product_dict["service"][21].id, "price_unit": 800},
            ],
            {start_date: "residual"},
        )
        intra_tax_ids = {}
        intra_b2b_fp = self.env["account.fiscal.position"].search(
            [("company_id", "=", self.id), ("fr_vat_type", "=", "intracom_b2b")],
            limit=1,
        )
        for tax_map_line in intra_b2b_fp.tax_ids:
            tax = tax_map_line.tax_dest_id
            if tax.type_tax_use == "purchase":
                rate = int(round(tax.amount * 10))
                intra_tax_ids[rate] = [Command.set([tax.id])]

        self._test_create_invoice_with_payment(
            "in_invoice",
            start_date,
            partner_dict["intracom_b2b"],
            [
                {
                    "account_id": account_dict["product"].id,
                    "tax_ids": intra_tax_ids[200],
                    "price_unit": 75,
                },
                {
                    "account_id": account_dict["service"].id,
                    "tax_ids": intra_tax_ids[200],
                    "price_unit": 25,
                },
                {
                    "account_id": account_dict["product"].id,
                    "tax_ids": intra_tax_ids[100],
                    "price_unit": 80,
                },
                {
                    "account_id": account_dict["service"].id,
                    "tax_ids": intra_tax_ids[100],
                    "price_unit": 30,
                },
                {
                    "account_id": account_dict["product"].id,
                    "tax_ids": intra_tax_ids[55],
                    "price_unit": 750,
                },
                {
                    "account_id": account_dict["service"].id,
                    "tax_ids": intra_tax_ids[55],
                    "price_unit": 250,
                },
                {
                    "account_id": account_dict["product"].id,
                    "tax_ids": intra_tax_ids[21],
                    "price_unit": 300,
                },
                {
                    "account_id": account_dict["service"].id,
                    "tax_ids": intra_tax_ids[21],
                    "price_unit": 800,
                },
            ],
            {start_date: "residual"},
        )
        # HA extracom
        self._test_create_invoice_with_payment(
            "in_invoice",
            start_date,
            partner_dict["extracom"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 200},
                {"product_id": product_dict["service"][200].id, "price_unit": 100},
                {"product_id": product_dict["product"][100].id, "price_unit": 110},
                {"product_id": product_dict["service"][100].id, "price_unit": 200},
                {"product_id": product_dict["product"][55].id, "price_unit": 500},
                {"product_id": product_dict["service"][55].id, "price_unit": 2500},
                {"product_id": product_dict["product"][21].id, "price_unit": 2000},
                {"product_id": product_dict["service"][21].id, "price_unit": 1100},
            ],
            {start_date: "residual"},
        )
        # ROYALTY
        if with_royalty:
            self._test_create_invoice_with_payment(
                "in_invoice",
                start_date,
                partner_dict["france_royalty"],
                [
                    {"product_id": product_dict["royalty"][100].id, "price_unit": 100},
                ],
                {start_date: "residual"},
            )

        # Add a cutoff move in a misc journal, to check that it doesn't impact
        # the amounts for the untaxed operations (E1 Extracom)
        self._test_create_cutoff_move(start_date)

    def _test_create_invoice_btp_subcontracting_data(
        self,
        start_date,
    ):
        product_dict = self._test_prepare_product_dict()
        partner_dict = self._test_prepare_partner_dict()
        self._test_prepare_expense_account_dict()
        # France exo customer invoice
        self._test_create_invoice_with_payment(
            "out_invoice",
            start_date,
            partner_dict["france_exo"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 600},
                {"product_id": product_dict["product"][100].id, "price_unit": 700},
                {"product_id": product_dict["product"][55].id, "price_unit": 800},
            ],
            {},
        )
        # France exo customer refund
        self._test_create_invoice_with_payment(
            "out_refund",
            start_date,
            partner_dict["france_exo"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 60},
                {"product_id": product_dict["product"][100].id, "price_unit": 70},
                {"product_id": product_dict["product"][55].id, "price_unit": 80},
            ],
            {},
        )
        # France exo vendor bill
        self._test_create_invoice_with_payment(
            "in_invoice",
            start_date,
            partner_dict["france_exo"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 400},
                {"product_id": product_dict["product"][100].id, "price_unit": 300},
                {"product_id": product_dict["product"][55].id, "price_unit": 200},
            ],
            {},
        )
        self._test_create_invoice_with_payment(
            "in_invoice",
            start_date,
            partner_dict["france_exo"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 200},
                {"product_id": product_dict["product"][100].id, "price_unit": 100},
                {"product_id": product_dict["product"][55].id, "price_unit": 50},
            ],
            {start_date: "residual"},
        )
        # France exo vendor refund
        self._test_create_invoice_with_payment(
            "in_refund",
            start_date,
            partner_dict["france_exo"],
            [
                {"product_id": product_dict["product"][200].id, "price_unit": 40},
                {"product_id": product_dict["product"][100].id, "price_unit": 30},
                {"product_id": product_dict["product"][55].id, "price_unit": 20},
            ],
            {start_date: "residual"},
        )

    def _test_create_cutoff_move(self, start_date):
        cdomain = [("company_id", "=", self.id)]
        aao = self.env["account.account"]
        pca_account = aao.search(cdomain + [("code", "=like", "487%")], limit=1)
        assert pca_account
        export_income_account = aao.search(cdomain + [("code", "=", "707400")], limit=1)
        assert export_income_account
        amount = 555.55
        move = self.env["account.move"].create(
            {
                "date": start_date,
                "journal_id": self.fr_vat_journal_id.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": export_income_account.id,
                            "debit": amount,
                        },
                    ),
                    Command.create(
                        {
                            "account_id": pca_account.id,
                            "credit": amount,
                        },
                    ),
                ],
            }
        )
        move.action_post()
