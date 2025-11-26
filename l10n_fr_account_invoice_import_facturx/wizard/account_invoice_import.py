# Copyright 2018-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountInvoiceImport(models.TransientModel):
    _inherit = "account.invoice.import"

    def prepare_facturx_xpath_dict(self):
        xpathd = super().prepare_facturx_xpath_dict()
        xpathd["partner"]["siret"] = [
            "//ram:ApplicableHeaderTradeAgreement"
            "/ram:SellerTradeParty"
            "/ram:SpecifiedLegalOrganization"
            "/ram:ID[@schemeID='0002']"
        ]
        xpathd["company"]["siret"] = [
            "//ram:ApplicableHeaderTradeAgreement"
            "/ram:BuyerTradeParty"
            "/ram:SpecifiedLegalOrganization"
            "/ram:ID[@schemeID='0002']"
        ]
        return xpathd

    # If one day we have a module l10n_fr_account_invoice_import
    # we could move the inherit of _prepare_new_partner_context() there
    @api.model
    def _prepare_create_invoice_no_partner(self, parsed_inv, import_config, vals):
        res = super()._prepare_create_invoice_no_partner(
            parsed_inv, import_config, vals
        )
        if (
            vals.get("import_partner_data")
            and isinstance(vals["import_partner_data"], dict)
            and parsed_inv.get("partner")
        ):
            if parsed_inv["partner"].get("siren"):
                vals["import_partner_data"]["siren"] = parsed_inv["partner"]["siren"]
            elif parsed_inv["partner"].get("siret"):
                vals["import_partner_data"]["siren"] = parsed_inv["partner"]["siret"][
                    :9
                ]
                vals["import_partner_data"]["nic"] = parsed_inv["partner"]["siret"][
                    9:14
                ]
        return res
