# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
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
    fr_vat_expense_analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account for Expense Adjustment",
        ondelete="restrict",
        check_company=True,
    )
    fr_vat_income_analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account for Income Adjustment",
        ondelete="restrict",
        check_company=True,
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

    @api.model
    def _test_fr_vat_create_company(
        self, company_name=None, fr_vat_exigibility="on_invoice"
    ):
        # I write this method here and not in the test,
        # because it can be very useful for demos too
        self = self.sudo()
        company = self.create(
            {
                "name": company_name or "FR Company VAT",
                "fr_vat_exigibility": fr_vat_exigibility,
                "street": "42 rue du logiciel libre",
                "zip": "69009",
                "city": "Lyon",
                "country_id": self.env.ref("base.fr").id,
                "siret": "77788899100018",
                "vat": "FR51777888991",
            }
        )
        self.env.user.write({"company_ids": [(4, company.id)]})
        fr_chart_template = self.env.ref("l10n_fr.l10n_fr_pcg_chart_template")
        fr_chart_template._load(20.0, 20.0, company)
        intracom_purchase_tax_dict = company._setup_l10n_fr_coa_vat_company()
        return (company, intracom_purchase_tax_dict)

    def _setup_l10n_fr_coa_vat_company(self):  # noqa: C901
        self.ensure_one()
        afpo = self.env["account.fiscal.position"]
        afpao = self.env["account.fiscal.position.account"]
        afpto = self.env["account.fiscal.position.tax"]
        aao = self.env["account.account"]
        ato = self.env["account.tax"]
        atrlo = self.env["account.tax.repartition.line"]
        od_journal = self.env["account.journal"].search(
            [("company_id", "=", self.id), ("type", "=", "general")], limit=1
        )
        self.write({"fr_vat_journal_id": od_journal.id})
        # Update PCG
        # delete some accounts
        accounts_to_del = aao.search(
            [
                ("company_id", "=", self.id),
                ("code", "in", ("701200", "707200", "445710")),
            ]
        )
        accounts_to_del.unlink()

        # create accounts
        revenue_accounts = [
            ("701200", "Vt produits finis UE B2B"),
            ("701300", "Vt produits finis UE B2C"),
            ("701400", "Vt produits finis reste du monde"),
            ("701500", "Vt produits finis France exonéré"),
            ("706200", "Prestation de service UE B2B"),
            ("706300", "Prestation de service UE B2C"),
            ("706400", "Prestation de service reste du monde"),
            ("706500", "Prestation de service France exonéré"),
            ("707200", "Vt marchandises UE B2B"),
            ("707300", "Vt marchandises UE B2C"),
            ("707400", "Vt marchandises reste du monde"),
            ("707500", "Vt marchandises France exonéré"),
            ("708520", "Frais de port UE B2B"),
            ("708530", "Frais de port UE B2C"),
            ("708540", "Frais de port reste du monde"),
            ("708550", "Frais de port France exonéré"),
        ]
        revenue_type_id = self.env.ref("account.data_account_type_revenue").id
        for acc_code, acc_name in revenue_accounts:
            aao.create(
                {
                    "company_id": self.id,
                    "code": acc_code,
                    "name": acc_name,
                    "user_type_id": revenue_type_id,
                    "reconcile": False,
                    "tax_ids": False,
                }
            )
        fr_account_codes = ["701100", "706000", "707100", "708500"]
        for fr_account_code in fr_account_codes:
            account = aao.search(
                [("company_id", "=", self.id), ("code", "=", fr_account_code)]
            )
            new_name = "%s France" % account.name
            account.write({"name": new_name})

        # update accounts
        mark_as_reconcile = ["445620", "445660"]
        for acc_code in mark_as_reconcile:
            account = aao.search(
                [
                    ("company_id", "=", self.id),
                    ("code", "=", acc_code),
                    ("reconcile", "=", False),
                ],
                limit=1,
            )
            if account:
                account.write({"reconcile": True})
        # update fiscal positions
        fp2type = {
            "fiscal_position_template_intraeub2b": "intracom_b2b",
            "fiscal_position_template_domestic": "france",
            "fiscal_position_template_import_export": "extracom",
            "fiscal_position_template_intraeub2c": "intracom_b2c",
        }
        type2map = {
            "intracom_b2b": [
                ("701100", "701200"),
                ("706000", "706200"),
                ("707100", "707200"),
                ("708500", "708520"),
                ("701500", "701200"),
                ("706500", "706200"),
                ("707500", "707200"),
                ("708550", "708520"),
            ],
            "intracom_b2c": [
                ("701100", "701300"),
                ("706000", "706300"),
                ("707100", "707300"),
                ("708500", "708530"),
            ],
            "extracom": [
                ("701100", "701400"),
                ("706000", "706400"),
                ("707100", "707400"),
                ("708500", "708540"),
                ("701500", "701400"),
                ("706500", "706400"),
                ("707500", "707400"),
                ("708550", "708540"),
            ],
            "france_exo": [
                ("701100", "701500"),
                ("706000", "706500"),
                ("707100", "707500"),
                ("708500", "708550"),
            ],
        }
        fptype2fp = {}
        for fp_xmlid_suffix, fp_type in fp2type.items():
            xmlid = "l10n_fr.%d_%s" % (self.id, fp_xmlid_suffix)
            fp = self.env.ref(xmlid)
            fpvals = {
                "fr_vat_type": fp_type,
                "auto_apply": False,
            }
            if fp_type == "france":
                fpvals["vat_required"] = False
            fp.write(fpvals)
            fptype2fp[fp_type] = fp
            if type2map.get(fp_type):
                for (src_acc_code, dest_acc_code) in type2map[fp_type]:
                    afpao.create(
                        {
                            "position_id": fp.id,
                            "account_src_id": aao.search(
                                [
                                    ("company_id", "=", self.id),
                                    ("code", "=", src_acc_code),
                                ]
                            ).id,
                            "account_dest_id": aao.search(
                                [
                                    ("company_id", "=", self.id),
                                    ("code", "=", dest_acc_code),
                                ]
                            ).id,
                        }
                    )
        # delete on_payment taxes
        taxes_to_del = ato.search(
            [("company_id", "=", self.id), ("tax_exigibility", "=", "on_payment")]
        )
        tax_map_to_del = afpto.search(
            [("company_id", "=", self.id), ("tax_src_id", "in", taxes_to_del.ids)]
        )
        tax_map_to_del.unlink()
        taxes_to_del.unlink()
        # Create supplier VAT on payment
        afpo.create(
            {
                "name": "France - Fournisseur TVA encaissement",
                "fr_vat_type": "france_vendor_vat_on_payment",
                "auto_apply": False,
                "company_id": self.id,
            }
        )
        # Create France exo FP
        france_exo_fp = afpo.create(
            {
                "name": "France exonéré",
                "fr_vat_type": "france_exo",
                "auto_apply": False,
                "company_id": self.id,
            }
        )
        fptype2fp["france_exo"] = france_exo_fp
        for (src_acc_code, dest_acc_code) in type2map["france_exo"]:
            afpao.create(
                {
                    "position_id": france_exo_fp.id,
                    "account_src_id": aao.search(
                        [
                            ("company_id", "=", self.id),
                            ("code", "=", src_acc_code),
                        ]
                    ).id,
                    "account_dest_id": aao.search(
                        [
                            ("company_id", "=", self.id),
                            ("code", "=", dest_acc_code),
                        ]
                    ).id,
                }
            )
        # I use extracom FP to get the list of source taxes
        extracom_fp = fptype2fp["extracom"]
        sale_tax_dest_xmlid = "l10n_fr.%d_tva_0" % self.id
        sale_tax_dest_id = self.env.ref(sale_tax_dest_xmlid).id
        # There is no puchase 0% tax provided in l10n_fr
        purchase_tax_dest_id = ato.create(
            {
                "company_id": self.id,
                "name": "TVA 0% (achat)",
                "description": "TVA 0%",
                "amount": 0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "tax_group_id": self.env.ref("l10n_fr.tax_group_tva_0").id,
                "invoice_repartition_line_ids": [
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                        },
                    ),
                ],
                "refund_repartition_line_ids": [
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                        },
                    ),
                ],
            }
        ).id

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

        # Update regular FR VAT taxes
        tax_type_id = self.env.ref("account.data_account_type_current_liabilities").id
        rate2account = {
            200: "445711",
            100: "445712",
            85: "445713",
            55: "445714",
            21: "445715",
        }
        for rate, acc_code in rate2account.items():
            rate_label = "%s %% " % str(rate / 10).replace(".", ",")
            tax_account_id = aao.create(
                {
                    "code": acc_code,
                    "name": "TVA collectée %s" % rate_label,
                    "company_id": self.id,
                    "reconcile": True,
                    "user_type_id": tax_type_id,
                }
            ).id
            rate2account[rate] = tax_account_id

        intracom_fp = fptype2fp["intracom_b2b"]
        for tline in intracom_fp.tax_ids:
            if tline.tax_src_id.type_tax_use == "sale":
                tax = tline.tax_src_id
                rate = int(round(tax.amount * 10))
                if rate in rate2account:
                    lines = atrlo.search(
                        [
                            "|",
                            ("invoice_tax_id", "=", tax.id),
                            ("refund_tax_id", "=", tax.id),
                            ("repartition_type", "=", "tax"),
                        ]
                    )
                    lines.write({"account_id": rate2account[rate]})
        # Update intracom and extracom autoliq taxes
        tracom_dict = {
            "intracom_b2b": {
                200: "445201",
                100: "445202",
                85: "445203",
                55: "445204",
                21: "445205",
                "deduc": "445662",
                "label": "acquisitions intracommunautaire",
            },
            "extracom": {
                200: "445301",
                100: "445302",
                85: "445303",
                55: "445304",
                21: "445305",
                "deduc": "445663",
                "label": "acquisitions extracommunautaire",
            },
        }
        intracom_purchase_tax_dict = {}
        for fp_type, wdict in tracom_dict.items():
            fp = fptype2fp[fp_type]
            deduc_tax_account_id = aao.create(
                {
                    "code": wdict["deduc"],
                    "name": "TVA déductible %s" % wdict["label"],
                    "company_id": self.id,
                    "reconcile": True,
                    "user_type_id": tax_type_id,
                }
            ).id
            for tax_line in fp.tax_ids:
                if tax_line.tax_dest_id.type_tax_use == "purchase":
                    tax = tax_line.tax_dest_id
                    tax_rate = int(round(tax.amount * 10))
                    rate_label = "%s %% " % str(tax_rate / 10).replace(".", ",")
                    if fp_type == "intracom_b2b":
                        intracom_purchase_tax_dict[tax_rate] = tax
                    if tax_rate in wdict:
                        acc_code = wdict[tax_rate]
                        due_tax_account_id = aao.create(
                            {
                                "code": acc_code,
                                "name": "TVA due %s %s" % (wdict["label"], rate_label),
                                "company_id": self.id,
                                "reconcile": True,
                                "user_type_id": tax_type_id,
                            }
                        ).id
                        deduc_lines = atrlo.search(
                            [
                                "|",
                                ("invoice_tax_id", "=", tax.id),
                                ("refund_tax_id", "=", tax.id),
                                ("repartition_type", "=", "tax"),
                                ("factor_percent", ">", 99),  # = 100
                            ]
                        )
                        deduc_lines.write({"account_id": deduc_tax_account_id})
                        due_lines = atrlo.search(
                            [
                                "|",
                                ("invoice_tax_id", "=", tax.id),
                                ("refund_tax_id", "=", tax.id),
                                ("repartition_type", "=", "tax"),
                                ("factor_percent", "<", -99),  # = -100
                            ]
                        )
                        due_lines.write({"account_id": due_tax_account_id})
        return intracom_purchase_tax_dict

    def _test_create_invoice_with_payment(
        self, move_type, date, partner, lines, payments, force_in_vat_on_payment=False
    ):
        self.ensure_one()
        amo = self.env["account.move"].with_company(self.id)
        amlo = self.env["account.move.line"].with_company(self.id)
        apro = self.env["account.payment.register"]
        journal_id = (
            amo.with_context(default_move_type=move_type, company_id=self.id)
            ._get_default_journal()
            .id
        )
        vals = {
            "company_id": self.id,
            "journal_id": journal_id,
            "move_type": move_type,
            "invoice_date": date,
            "partner_id": partner.id,
            "currency_id": self.currency_id.id,
            "invoice_line_ids": [],
        }
        vals = amo.play_onchanges(vals, ["partner_id"])
        for line in lines:
            il_vals = dict(line, move_id=vals)
            if "quantity" not in il_vals:
                il_vals["quantity"] = 1
            if line.get("product_id"):
                il_vals = amlo.play_onchanges(il_vals, ["product_id"])
            il_vals.pop("move_id")
            vals["invoice_line_ids"].append((0, 0, il_vals))
        move = amo.create(vals)
        if move_type in ("in_invoice", "in_refund") and force_in_vat_on_payment:
            move.write({"in_vat_on_payment": True})
        move.action_post()

        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", self.id)], limit=1
        )
        if move_type in ("out_invoice", "in_refund"):
            payment_method_id = self.env.ref(
                "account.account_payment_method_manual_in"
            ).id
        else:
            payment_method_id = self.env.ref(
                "account.account_payment_method_manual_out"
            ).id
        assert bank_journal
        ctx = {"active_model": "account.move", "active_ids": [move.id]}
        for (pay_date, payment_ratio) in payments.items():
            vals = {
                "journal_id": bank_journal.id,
                "payment_method_id": payment_method_id,
                "payment_date": pay_date,
            }
            if payment_ratio != "residual":
                assert payment_ratio > 0 and payment_ratio < 100
                vals["amount"] = self.currency_id.round(
                    move.amount_total * payment_ratio / 100
                )
            payment_wiz = apro.with_context(ctx).create(vals)
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
        taxes = self.env["account.tax"].search(
            [
                ("company_id", "=", self.id),
                ("type_tax_use", "=", type_tax_use),
                ("amount_type", "=", "percent"),
                ("price_include", "=", False),
                ("fr_vat_autoliquidation", "=", False),
            ]
        )
        for tax in taxes:
            if not asset and "immobilisation" in tax.name:
                continue
            if asset and "immobilisation" not in tax.name:
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
                sale_tax = self.env.ref("l10n_fr.%d_tva_0" % self.id)
                sale_tax_ids = [(6, 0, [sale_tax.id])]
                purchase_tax_ids = False
                account_income_id = self._test_get_account("707500")
            product = ppo.create(
                {
                    "name": "Test-demo TVA %s %%" % real_vat_rate,
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
        intracom_purchase_tax_dict,
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
        for rate, tax in intracom_purchase_tax_dict.items():
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
                {"product_id": product_dict["service"][200].id, "price_unit": 300},
                {"product_id": product_dict["service"][100].id, "price_unit": 310},
                {"product_id": product_dict["service"][55].id, "price_unit": 3000},
                {"product_id": product_dict["service"][21].id, "price_unit": 3100},
            ],
            {start_date: "residual"},
        )
