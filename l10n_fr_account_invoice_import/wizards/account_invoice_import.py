# Copyright 2026 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from stdnum.fr.siren import is_valid as siren_is_valid
from stdnum.fr.siren import to_tva
from stdnum.fr.siret import is_valid as siret_is_valid

from odoo import api, models


class AccountInvoiceImport(models.TransientModel):
    _inherit = "account.invoice.import"

    @api.model
    def _update_import_config(self, import_config, speedy=None):
        res = super()._update_import_config(import_config, speedy=speedy)
        fpos_obj = self.env["account.fiscal.position"]
        if hasattr(fpos_obj, "fr_vat_type") and import_config["invoice_type"] == "in":
            fpos_ids = list(
                fpos_obj._search(
                    [
                        ("company_id", "=", import_config["company"].id),
                        ("fr_vat_type", "=", "france_vendor_vat_on_payment"),
                    ],
                    limit=1,
                )
            )
            if fpos_ids:
                import_config["fr_vendor_vat_on_payment_fiscal_position_id"] = fpos_ids[
                    0
                ]
        return res

    @api.model
    def _prepare_create_invoice_vals(self, parsed_inv, import_config):
        vals = super()._prepare_create_invoice_vals(parsed_inv, import_config)
        incoterms_code2id = import_config["speedy"]["incoterms_code2id"]
        if (
            parsed_inv.get("EXT-FR-FE-185")
            and parsed_inv["EXT-FR-FE-185"] in incoterms_code2id
        ):
            vals.update(
                {
                    "invoice_incoterm_id": incoterms_code2id[
                        parsed_inv["EXT-FR-FE-185"]
                    ],
                    "incoterm_location": parsed_inv.get("EXT-FR-FE-186"),
                }
            )
        if (
            import_config["invoice_type"] == "in"
            and import_config.get("fr_vendor_vat_on_payment_fiscal_position_id")
            and parsed_inv.get("BG-4", {}).get("country_code") == "FR"
            and parsed_inv.get("BT-8") == "payment"
        ):
            vals["fiscal_position_id"] = import_config[
                "fr_vendor_vat_on_payment_fiscal_position_id"
            ]
        return vals

    @api.model
    def _match_partner(self, parsed_inv, import_config):
        partner = super()._match_partner(parsed_inv, import_config)
        if partner:
            return partner
        partner_dict = self._get_partner_dict(parsed_inv, import_config)
        base_domain = [
            ("company_id", "in", (import_config["company"].id, False)),
            ("parent_id", "=", False),
        ]
        if (
            partner_dict.get("legal_identifier_schemeid") == "0002"
            and partner_dict.get("legal_identifier")
            and siren_is_valid(partner_dict["legal_identifier"])
        ):
            siren = partner_dict["legal_identifier"]
            vat_from_siren = f"FR{to_tva(siren)}"
            partner = self.env["res.partner"].search(
                base_domain
                + ["|", ("siren", "=", siren), ("vat", "=", vat_from_siren)],
                limit=1,
                order=import_config["partner_match_order"],
            )
            if partner:
                msg = (
                    f"Partner {partner.display_name} matched via SIREN "
                    "(possiblity using the french VAT number in Odoo)"
                )
                self._info_log(import_config, msg)
                return partner
        return partner

    @api.model
    def _prepare_create_invoice_no_partner(self, parsed_inv, import_config, vals):
        res = super()._prepare_create_invoice_no_partner(
            parsed_inv, import_config, vals
        )
        partner_dict = self._get_partner_dict(parsed_inv, import_config)
        if (
            vals.get("import_partner_data")
            and partner_dict.get("legal_identifier_schemeid") == "0002"
            and partner_dict.get("legal_identifier")
            and siren_is_valid(partner_dict["legal_identifier"])
        ):
            siren = partner_dict["legal_identifier"]
            vals["import_partner_data"]["siren"] = siren
            if partner_dict.get("identifiers", {}).get("0009"):
                siret = partner_dict["identifiers"]["0009"]
                if siret_is_valid(siret):
                    vals["import_partner_data"]["nic"] = siret[9:]
        return res
