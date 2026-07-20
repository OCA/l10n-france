# Copyright 2024 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _fr_account_tax_unece_data(self):
        xmlid2id = {
            "type_vat": self.env.ref("account_tax_unece.tax_type_vat").id,
            "categ_s": self.env.ref("account_tax_unece.tax_categ_s").id,
            "categ_k": self.env.ref("account_tax_unece.tax_categ_k").id,
            "categ_g": self.env.ref("account_tax_unece.tax_categ_g").id,
            "categ_e": self.env.ref("account_tax_unece.tax_categ_e").id,
        }
        res = {}
        tax_data = self._parse_csv("fr", "account.tax")
        for tax_xmlid in tax_data.keys():
            res[tax_xmlid] = {
                "unece_type_id": xmlid2id["type_vat"],
            }
            if "_intra_" in tax_xmlid:
                res[tax_xmlid]["unece_categ_id"] = xmlid2id["categ_k"]
            elif "_export" in tax_xmlid or "_import" in tax_xmlid:
                res[tax_xmlid]["unece_categ_id"] = xmlid2id["categ_g"]
            elif "_imm_" in tax_xmlid or "_fuel" in tax_xmlid:
                res[tax_xmlid]["unece_categ_id"] = False
            elif tax_xmlid.endswith(("_good_0", "_service_0")):
                res[tax_xmlid]["unece_categ_id"] = xmlid2id["categ_e"]
            else:
                res[tax_xmlid]["unece_categ_id"] = xmlid2id["categ_s"]
        return res

    @template("fr", "account.tax")
    def _get_fr_account_tax(self):
        return self._fr_account_tax_unece_data()
