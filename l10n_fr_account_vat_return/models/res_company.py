# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


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
        [
            ("on_invoice", "Based on invoice"),
            ("on_payment", "Based on payment"),
            ("auto", "Both (automatic)"),
        ],
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
    def _test_fr_vat_create_company(self):
        # I write this method here and not in the test,
        # because it can be very useful for demos too
        self = self.sudo()
        afpao = self.env["account.fiscal.position.account"]
        afpto = self.env["account.fiscal.position.tax"]
        aao = self.env["account.account"]
        ato = self.env["account.tax"]
        atrlo = self.env["account.tax.repartition.line"]
        company = self.create(
            {
                "name": "FR Company VAT",
                "fr_vat_exigibility": "on_payment",
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
        od_journal = self.env["account.journal"].search(
            [("company_id", "=", company.id), ("type", "=", "general")], limit=1
        )
        company.write({"fr_vat_journal_id": od_journal.id})
        # TODO create company bank account
        # create accounts
        revenue_accounts = [
            ("701300", "Vt produits finis UE B2B"),
            ("701400", "Vt produits finis UE B2C"),
            ("701500", "Vt produits finis reste du monde"),
            ("706300", "Prestation de service UE B2B"),
            ("706400", "Prestation de service UE B2C"),
            ("706500", "Prestation de service reste du monde"),
            ("707300", "Vt marchandises UE B2B"),
            ("707400", "Vt marchandises UE B2C"),
            ("707500", "Vt marchandises reste du monde"),
            ("708530", "Frais de port UE B2B"),
            ("708540", "Frais de port UE B2C"),
            ("708550", "Frais de port reste du monde"),
        ]
        self.env["account.account"].search(
            [("company_id", "=", company.id), ("code", "=", "707200")]
        ).unlink()
        self.env["account.account"].search(
            [("company_id", "=", company.id), ("code", "=", "701200")]
        ).unlink()
        # Update PCG
        revenue_type_id = self.env.ref("account.data_account_type_revenue").id
        for acc_code, acc_name in revenue_accounts:
            aao.create(
                {
                    "company_id": company.id,
                    "code": acc_code,
                    "name": acc_name,
                    "user_type_id": revenue_type_id,
                    "reconcile": False,
                }
            )
        fr_account_codes = ["701100", "706000", "707100", "708500"]
        for fr_account_code in fr_account_codes:
            account = aao.search(
                [("company_id", "=", company.id), ("code", "=", fr_account_code)]
            )
            new_name = "%s France" % account.name
            account.write({"name": new_name})

        # Update taxes
        rate2code = {
            20.0: "445711",
            10.0: "445712",
            8.5: "445713",
            5.5: "445714",
            2.1: "445715",
        }
        tax_type_id = self.env.ref("account.data_account_type_current_liabilities").id
        for rate, acc_code in rate2code.items():
            tax_account = aao.create(
                {
                    "code": acc_code,
                    "name": "TVA collectée %s %%" % rate,
                    "company_id": company.id,
                    "reconcile": True,
                    "user_type_id": tax_type_id,
                }
            )
            taxes = ato.search(
                [
                    ("company_id", "=", company.id),
                    ("type_tax_use", "=", "sale"),
                    ("amount_type", "=", "percent"),
                    ("amount", "=", rate),
                ]
            )
            lines = atrlo.search(
                [
                    "|",
                    ("invoice_tax_id", "in", taxes.ids),
                    ("refund_tax_id", "in", taxes.ids),
                    ("repartition_type", "=", "tax"),
                    ("account_id", "!=", False),
                ]
            )
            lines.write({"account_id": tax_account.id})

        accounts_to_del = aao.search(
            [
                ("company_id", "=", company.id),
                ("code", "in", ("701200", "707200", "445710")),
            ]
        )
        accounts_to_del.unlink()
        # update fiscal positions
        fp2type = {
            "fiscal_position_template_intraeub2b": "intracom_b2b",
            "fiscal_position_template_domestic": "france",
            "fiscal_position_template_import_export": "extracom",
            "fiscal_position_template_intraeub2c": "intracom_b2c",
        }
        type2map = {
            "intracom_b2b": [
                ("701100", "701300"),
                ("706000", "706300"),
                ("707100", "707300"),
                ("708500", "708530"),
            ],
            "intracom_b2c": [
                ("701100", "701400"),
                ("706000", "706400"),
                ("707100", "707400"),
                ("708500", "708540"),
            ],
            "extracom": [
                ("701100", "701500"),
                ("706000", "706500"),
                ("707100", "707500"),
                ("708500", "708550"),
            ],
        }
        for fp_xmlid_suffix, fp_type in fp2type.items():
            xmlid = "l10n_fr.%d_%s" % (company.id, fp_xmlid_suffix)
            fp = self.env.ref(xmlid)
            fp.write(
                {
                    "fr_vat_type": fp_type,
                    "auto_apply": False,
                }
            )
            if type2map.get(fp_type):
                for (src_acc_code, dest_acc_code) in type2map[fp_type]:
                    afpao.create(
                        {
                            "position_id": fp.id,
                            "account_src_id": aao.search(
                                [
                                    ("company_id", "=", company.id),
                                    ("code", "=", src_acc_code),
                                ]
                            ).id,
                            "account_dest_id": aao.search(
                                [
                                    ("company_id", "=", company.id),
                                    ("code", "=", dest_acc_code),
                                ]
                            ).id,
                        }
                    )
        # delete on_payment taxes
        taxes_to_del = ato.search(
            [("company_id", "=", company.id), ("tax_exigibility", "=", "on_payment")]
        )
        tax_map_to_del = afpto.search(
            [("company_id", "=", company.id), ("tax_src_id", "in", taxes_to_del.ids)]
        )
        tax_map_to_del.unlink()
        taxes_to_del.unlink()
        return company
