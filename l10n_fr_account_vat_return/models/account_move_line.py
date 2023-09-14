# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


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
