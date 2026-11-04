# Copyright 2004-2015 Odoo S.A. (https://odoo.com)
# Copyright 2026 Le Filament (https://le-filament.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, models

from .account_edi_xml_ubl_21_fr import (
    CPRO_CUSTOMIZATION_ID,
    PDP_CUSTOMIZATION_ID,
)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        # Extends account_edi_ubl_cii
        customization_id = tree.findtext("{*}CustomizationID")
        # Note: The CustomizationID alone is not enough because
        # e.g. SuperPDP just sends `urn:cen.eu:en16931:2017`
        # but still expects the full French validation.
        if customization_id == CPRO_CUSTOMIZATION_ID:
            return self.env["account.edi.xml.ubl_21_fr"]
        if customization_id == PDP_CUSTOMIZATION_ID:
            receiver_endpoint_node = tree.find(
                "./{*}AccountingCustomerParty/{*}Party/{*}EndpointID"
            )
            if (
                receiver_endpoint_node is not None
                and receiver_endpoint_node.get("schemeID") == "0225"
            ):
                return self.env["account.edi.xml.ubl_21_fr"]
        return super()._get_ubl_cii_builder_from_xml_tree(tree)

    def _l10n_fr_get_reconciled_amls(self):
        self.ensure_one()
        counterpart_move_type = (
            "out_invoice" if self.move_type == "out_refund" else "out_refund"
        )
        return self._get_reconciled_amls().filtered(
            lambda line: line.move_id.move_type != counterpart_move_type
        )

    def _l10n_fr_get_payment_date(self):
        reconciled_amls = self._l10n_fr_get_reconciled_amls()
        if not reconciled_amls:
            return None
        return max(aml.date for aml in reconciled_amls)
