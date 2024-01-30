# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.tools import float_compare


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
    fr_vat_expense_analytic_distribution = fields.Json(
        string="Analytic for Expense Adjustment",
        compute="_compute_fr_vat_analytic_distribution",
        store=True,
        readonly=False,
        precompute=True,
    )
    fr_vat_income_analytic_distribution = fields.Json(
        string="Analytic for Income Adjustment",
        compute="_compute_fr_vat_analytic_distribution",
        store=True,
        readonly=False,
        precompute=True,
    )
    analytic_precision = fields.Integer(
        default=lambda self: self.env["decimal.precision"].precision_get(
            "Percentage Analytic"
        ),
    )
    fr_vat_bank_account_id = fields.Many2one(
        "res.partner.bank",
        string="Company Bank Account",
        check_company=True,
        ondelete="restrict",
        help="Company bank account used to pay VAT or receive credit VAT reimbursements.",
    )

    @api.model
    def _fr_vat_exigibility_selection(self):
        res = [
            ("on_invoice", _("Based on invoice")),
            ("on_payment", _("Based on payment")),
            ("auto", _("Both (automatic)")),
        ]
        return res

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
        self.env.user.write({"company_ids": [(4, company.id)]})
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
        self.write(
            {
                "fr_vat_journal_id": od_journal.id,
                "fr_vat_bank_account_id": self.partner_id.bank_ids[0].id,
            }
        )
        # activate all taxes
        ato.search(cdomain + [("active", "=", False)]).write({"active": True})
        # Create France exo FP
        france_exo_fp = afpo.create(
            {
                "name": "France exonéré",
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
        for (src_acc_code, dest_acc_code) in exo_fp_account_map.items():
            src_account = aao.search(cdomain + [("code", "=", src_acc_code)], limit=1)
            assert src_account
            dest_account = aao.create(
                {
                    "company_id": self.id,
                    "code": dest_acc_code,
                    "name": "%s exonéré" % src_account.name,
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
        tax_0_xmlid = "l10n_fr_oca.%d_tva_%s_0_exo"
        sale_tax_dest_id = self.env.ref(tax_0_xmlid % (self.id, "sale")).id
        purchase_tax_dest_id = self.env.ref(tax_0_xmlid % (self.id, "purchase")).id

        for extracom_tax_line in extracom_fp.tax_ids:
            if extracom_tax_line.tax_src_id.type_tax_use == "sale":
                tax_dest_id = sale_tax_dest_id
            else:
                tax_dest_id = purchase_tax_dest_id
            afpto.create(
                {
                    "position_id": france_exo_fp.id,
                    "tax_src_id": extracom_tax_line.tax_src_id.id,
                    "tax_dest_id": tax_dest_id,
                }
            )
        # Update account mapping on IntraEU B2B and Export
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
        move = amo.create(vals)
        if move_type in ("in_invoice", "in_refund") and force_in_vat_on_payment:
            move.write({"in_vat_on_payment": True})
        move.action_post()

        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", self.id)], limit=1
        )
        assert bank_journal
        for (pay_date, payment_ratio) in payments.items():
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
        # I can't use product_type="product" because this module
        # doesn't depend on the module "stock"
        ppo = self.env["product.product"].with_company(self.id)
        for vat_rate in product_dict.keys():
            if vat_rate == 21 and asset:
                continue
            if vat_rate:
                real_vat_rate = vat_rate / 10
                sale_tax = self._test_get_tax("sale", real_vat_rate)
                assert sale_tax
                sale_tax_ids = [(6, 0, [sale_tax.id])]
                purchase_tax = self._test_get_tax(
                    "purchase", real_vat_rate, asset=asset
                )
                assert purchase_tax
                purchase_tax_ids = [(6, 0, [purchase_tax.id])]
                account_income_id = False
            else:
                real_vat_rate = 0
                exo_tax_xmlid = "l10n_fr_oca.%d_tva_%s_0_exo"
                sale_tax = self.env.ref(exo_tax_xmlid % (self.id, "sale"))
                sale_tax_ids = [(6, 0, [sale_tax.id])]
                purchase_tax = self.env.ref(exo_tax_xmlid % (self.id, "purchase"))
                purchase_tax_ids = [(6, 0, [purchase_tax.id])]
                account_income_id = self._test_get_account("707500")
            product_name = "Test-demo %s%s TVA %s %%" % (
                product_type,
                real_vat_rate,
                asset and " immo" or "",
            )
            product = ppo.create(
                {
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
            )
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
        }
        self._test_common_product_dict(product_dict["product"])
        self._test_common_product_dict(product_dict["asset"], asset=True)
        self._test_common_product_dict(product_dict["service"], product_type="service")
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
            "intracom_b2b": False,
            #  "intracom_b2c": False,
            "extracom": False,
            "france_exo": False,
        }
        afpo = self.env["account.fiscal.position"]
        rpo = self.env["res.partner"].with_company(self.id)
        for fr_vat_type in partner_dict.keys():
            fiscal_position = afpo.search(
                [("company_id", "=", self.id), ("fr_vat_type", "=", fr_vat_type)],
                limit=1,
            )
            if fiscal_position:
                # to avoid error on invoice validation
                if fr_vat_type == "intracom_b2b":
                    fiscal_position.write({"vat_required": False})
                partner = rpo.create(
                    {
                        "is_company": True,
                        "name": "Test-demo %s" % fr_vat_type,
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
                    (
                        0,
                        0,
                        {
                            "account_id": credit_acc.id,
                            "debit": amount,
                        },
                    ),
                    (
                        0,
                        0,
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
        self,
        start_date,
        extracom_refund_ratio=0.5,
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
                intra_tax_ids[rate] = [(6, 0, [tax.id])]

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
        # Add a cutoff move in a misc journal, to check that it doesn't impact
        # the amounts for the untaxed operations (E1 Extracom)
        self._test_create_cutoff_move(start_date)

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
                    (
                        0,
                        0,
                        {
                            "account_id": export_income_account.id,
                            "debit": amount,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": pca_account.id,
                            "credit": amount,
                        },
                    ),
                ],
            }
        )
        move.action_post()
