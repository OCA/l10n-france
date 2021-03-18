# Copyright 2015-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from stdnum.fr.siren import validate as siren_validate
from stdnum.fr.siret import validate as siret_validate

from odoo import _, api, models


class BusinessDocumentImport(models.AbstractModel):
    _inherit = "business.document.import"

    @api.model
    def _hook_match_partner(self, partner_dict, chatter_msg, domain, order):
        rpo = self.env["res.partner"]
        if partner_dict.get("siret"):
            siret = partner_dict["siret"].replace(" ", "")
            if siret_validate(siret):
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
            if siren_validate(siren):
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
    def user_error_wrap(self, method, data_dict, error_msg):
        if method == "_match_partner" and error_msg and data_dict:
            error_msg += "SIREN: {}\nSIRET: {}\n".format(
                data_dict.get("siren"),
                data_dict.get("siret"),
            )
        return super().user_error_wrap(method, data_dict, error_msg)

    @api.model
    def _check_company(self, company_dict, chatter_msg):
        if not company_dict:
            company_dict = {}
        rco = self.env["res.company"]
        if self._context.get("force_company"):
            company = rco.browse(self._context["force_company"])
        else:
            company = self.env.company
        siren = False
        if company_dict.get("siret"):
            siret = company_dict["siret"].replace(" ", "")
            siren = siret[:9]
        if company_dict.get("siren"):
            siren = company_dict["siren"].replace(" ", "")
        if siren and siren_validate(siren):
            if company.siren:
                if company.siren != siren:
                    raise self.user_error_wrap(
                        "_check_company",
                        company_dict,
                        _(
                            "The SIREN of the customer written in the "
                            "business document (%s) doesn't match the SIREN "
                            "of the company '%s' (%s) in which you are "
                            "trying to import this document."
                        )
                        % (siren, company.display_name, company.siren),
                    )
            else:
                chatter_msg.append(
                    _("Missing SIRET on company '%s'") % company.display_name
                )
        return super()._check_company(company_dict, chatter_msg)
