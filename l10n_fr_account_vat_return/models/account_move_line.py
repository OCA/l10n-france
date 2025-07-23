# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.tools.misc import format_amount, format_date


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _fr_product_account_prefixes(self):
        return (
            "21",
            # expenses
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
            # revenue
            "701",
            "702",
            "703",
            "707",
            "7085",
            "7091",
            "7092",
            "7093",
            "7097",
        )

    def _fr_is_product_or_service(self):
        self.ensure_one()
        assert self.display_type == "product"
        res = "service"
        if self.product_id:
            if (
                self.product_id.type in ("product", "consu")
                or self.product_id.is_accessory_cost
            ):
                res = "product"
        else:
            product_account_prefixes = self._fr_product_account_prefixes()
            if self.account_id.code.startswith(product_account_prefixes):
                res = "product"
        return res

    def _prepare_xlsx_zip_deductible_vat(self, wdict, attach_threshold=None):
        self.ensure_one()
        styles = wdict["styles"]
        move = self.move_id
        res = {
            "date": (move.date, styles["regular_date"]),
            "move.name": (move.name, styles["regular"]),
            "journal": (move.journal_id.name, styles["regular"]),
            "account": (self.account_id.display_name, styles["regular"]),
            "debit": (self.debit, styles["regular_company_currency"]),
            "credit": (self.credit, styles["regular_company_currency"]),
        }
        if move.move_type not in ("in_refund", "in_invoice"):
            res["inv"] = ("non", styles["regular_center_warn"])
            return res

        currency = move.currency_id
        sign = move.move_type in ("in_refund", "out_refund") and -1 or 1
        if currency == self.company_id.currency_id:
            cur_style = styles["regular_company_currency"]
        else:
            cur_style_name = f"regular_currency_{currency.name}"
            if cur_style_name not in styles:
                cents = "0" * currency.decimal_places
                if currency.position == "before":
                    num_format = f"{currency.symbol} # ### ##0.{cents}"
                else:
                    num_format = f"# ### ##0.{cents} {currency.symbol}"
                styles[cur_style_name] = wdict["workbook"].add_format(
                    {"num_format": num_format}
                )
            cur_style = styles[cur_style_name]

        if hasattr(self.partner_id, "siren"):
            siren = self.partner_id.siren
        else:
            siren = self.partner_id.siret and self.partner_id.siret.strip()[:9]

        if (
            attach_threshold
            and self.company_id.currency_id.compare_amounts(
                abs(move.amount_untaxed_signed), attach_threshold
            )
            < 0
        ):
            attach_threshold_fmt = format_amount(
                self.env,
                attach_threshold,
                self.company_id.currency_id,
                lang_code="fr_FR",
            )
            attach_value = f"non car < {attach_threshold_fmt} HT"
            attach_style = "regular_center"
        else:
            if move.id not in wdict["move_id2filename"]:
                attach_domain = [
                    ("res_model", "=", "account.move"),
                    ("res_id", "=", move.id),
                    ("type", "=", "binary"),
                ]
                iao = self.env["ir.attachment"]
                attach = iao.search(
                    [("mimetype", "=", "application/pdf")] + attach_domain, limit=1
                )
                if not attach:
                    attach = iao.search(
                        [("mimetype", "in", ("image/jpeg", "application/xml"))]
                        + attach_domain,
                        limit=1,
                    )
                if attach:
                    filename = ".".join(
                        [move.name.replace("/", "_"), attach.mimetype.split("/")[1]]
                    )
                    wdict["zip_file"].writestr(f"factures/{filename}", attach.raw)
                    wdict["move_id2filename"][move.id] = filename

            if move.id in wdict["move_id2filename"]:
                attach_value = wdict["move_id2filename"][move.id]
                attach_style = "regular_center"
            else:
                attach_value = "manquant"
                attach_style = "regular_center_warn"

        fp = move.fiscal_position_id
        if fp and fp.fr_vat_type == "france_vendor_vat_on_payment":
            vat_on_payment = True
        else:
            vat_on_payment = False

        res.update(
            {
                "inv": ("oui", styles["regular_center"]),
                "supplier.name": (self.partner_id.name or "", styles["regular"]),
                "supplier.siren": (siren or "", styles["regular"]),
                "supplier.vat": (self.partner_id.vat or "", styles["regular"]),
                "inv.date": (move.invoice_date, styles["regular_date"]),
                "inv.ref": (move.ref or "", styles["regular"]),
                "inv.currency": (currency.name, styles["regular_center"]),
                "inv.untaxed": (move.amount_untaxed * sign, cur_style),
                "inv.total": (move.amount_total * sign, cur_style),
                "inv.vat_on_payment": (
                    vat_on_payment and "oui" or "non",
                    styles["regular_center"],
                ),
                "inv.attach": (attach_value, styles[attach_style]),
            }
        )
        if vat_on_payment:
            res["inv.residual"] = (move.amount_residual * sign, cur_style)
            pay_infos = (
                isinstance(move.invoice_payments_widget, dict)
                and move.invoice_payments_widget["content"]
                or []
            )
            content = []
            for payment in pay_infos:
                if payment["date"] and payment["amount"]:
                    # XLSX is for DGFiP, so we write directly in French
                    pay_amount_fmt = format_amount(
                        self.env,
                        payment["amount"],
                        move.currency_id,
                        lang_code="fr_FR",
                    )
                    pay_date_fmt = format_date(
                        self.env, payment["date"], lang_code="fr_FR"
                    )
                    content.append(f"{pay_amount_fmt} payé le {pay_date_fmt}")
            if content:
                res["inv.payments"] = (", ".join(content), styles["regular"])

        return res
