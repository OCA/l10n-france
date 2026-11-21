# Copyright 2026 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from stdnum.fr.siren import is_valid as siren_is_valid, to_tva
from stdnum.fr.siret import is_valid as siret_is_valid

from odoo import _, api, models
from odoo.exceptions import UserError


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

    def _check_import_company(self, parsed_inv, import_config):
        res = super()._check_import_company(parsed_inv, import_config)
        company = import_config["company"]
        company_dict = self._get_company_dict(parsed_inv, import_config)
        company_siren = company.partner_id._get_siren()
        if (
            company_dict
            and company_dict.get("legal_identifier_schemeid") == "0002"
            and company_dict.get("legal_identifier")
            and siren_is_valid(company_dict["legal_identifier"])
            and company_siren
        ):
            invoice_siren = (
                "".join(
                    x for x in company_dict["legal_identifier"] if not x.isspace()
                ).upper()
                or False
            )
            if invoice_siren != company_siren:
                raise UserError(
                    _(
                        "Trying to import invoice in company %(company)s "
                        "that has SIREN '%(company_siren)s' but "
                        "the SIREN of the destination company written in "
                        "the invoice to import is '%(invoice_siren)s'.",
                        company=company.display_name,
                        company_siren=company_siren,
                        invoice_siren=invoice_siren,
                    )
                )
        return res
