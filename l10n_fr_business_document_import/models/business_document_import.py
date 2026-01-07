# Copyright 2015-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from stdnum.fr.siren import is_valid as siren_is_valid
from stdnum.fr.siret import is_valid as siret_is_valid

from odoo import _, api, models


class BusinessDocumentImport(models.AbstractModel):
    _inherit = "business.document.import"

    @api.model
    def _hook_match_partner(self, partner_dict, chatter_msg, domain, order):
        rpo = self.env["res.partner"]
        if partner_dict.get("siret"):
            siret = partner_dict["siret"].replace(" ", "")
            if siret_is_valid(siret):
                partner = rpo.search(
                    domain + [("siret", "=", siret)], order=order, limit=1
                )
                if partner:
                    return partner
                # fallback on siren search
                elif not partner_dict.get("siren"):
                    partner_dict["siren"] = siret[:9]
        if partner_dict.get("siren"):
            # when partner_dict comes from invoice2data, siren may be an int
            if isinstance(partner_dict["siren"], int):
                siren = str(partner_dict["siren"])
            else:
                siren = partner_dict["siren"].replace(" ", "")
            if siren_is_valid(siren):
                partner = rpo.search(
                    domain
                    + [
                        ("parent_id", "=", False),
                        ("siren", "=", siren),
                    ],
                    limit=1,
                    order=order,
                )
                if partner:
                    return partner
        return super()._hook_match_partner(partner_dict, chatter_msg, domain, order)

    @api.model
    def user_error_wrap(
        self, method, data_dict, error_msg, chatter_msg, raise_exception
    ):
        if method == "_match_partner" and error_msg and data_dict:
            error_msg += "SIREN: {}\nSIRET: {}\n".format(
                data_dict.get("siren") or "",
                data_dict.get("siret") or "",
            )
        return super().user_error_wrap(
            method, data_dict, error_msg, chatter_msg, raise_exception
        )

    @api.model
    def _check_company(
        self, company_dict, chatter_msg, company=None, raise_exception=True
    ):
        if not company_dict:
            company_dict = {}
        if company is None:
            if (
                self._context.get("allowed_company_ids")
                and len(self._context["allowed_company_ids"]) == 1
            ):
                company = self.env["res.company"].browse(
                    self._context["allowed_company_ids"][0]
                )
            else:
                company = self.env.company
        siren = False
        if company_dict.get("siret"):
            siret = company_dict["siret"].replace(" ", "")
            siren = siret[:9]
        if company_dict.get("siren"):
            siren = company_dict["siren"].replace(" ", "")
        if siren and siren_is_valid(siren):
            if company.siren:
                if company.siren != siren:
                    self.user_error_wrap(
                        "_check_company",
                        company_dict,
                        _(
                            "The SIREN of the customer written in the "
                            "business document (%(customer_siren)s) doesn't match "
                            "the SIREN of the company '%(company_name)s' "
                            "(%(company_siren)s) in which you are trying to import "
                            "this document.",
                            customer_siren=siren,
                            company_name=company.display_name,
                            company_siren=company.siren,
                        ),
                        chatter_msg,
                        raise_exception,
                    )
            elif (
                company.country_id
                and company.country_id.code
                in self.env["res.company"]._get_france_country_codes()
            ):
                msg = _("Missing SIRET on company '%s'.") % company.display_name
                if msg not in chatter_msg:
                    chatter_msg.append(msg)
        return super()._check_company(
            company_dict, chatter_msg, company=company, raise_exception=raise_exception
        )
