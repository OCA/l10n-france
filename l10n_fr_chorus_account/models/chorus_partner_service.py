# Copyright 2018-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

logger = logging.getLogger(__name__)


class ChorusPartnerService(models.Model):
    _name = "chorus.partner.service"
    _description = "Chorus Services attached to a partner"
    _order = "partner_id, code"

    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        ondelete="cascade",
        domain=[("parent_id", "=", False)],
    )
    code = fields.Char(string="Service Code", required=True)
    active = fields.Boolean(default=True)
    name = fields.Char(string="Service Name", required=True)
    chorus_identifier = fields.Integer(readonly=True)
    engagement_required = fields.Boolean()

    @api.constrains("code")
    def _check_service_factures_publiques_dont_use(self):
        # As explained on
        # https://communaute.chorus-pro.gouv.fr/documentation/
        # guide-dutilisation-de-lannuaire-des-structures-publiques-dans-chorus-pro/
        # "Le Service des factures publiques est exclusivement dédié à la
        # facturation intra-sphère publique.
        # If we use this service, the flux will be rejected
        for service in self:
            if service.code == "FACTURES_PUBLIQUES":
                raise ValidationError(
                    _(
                        "The 'Service des factures publiques' with code "
                        "'FACTURES_PUBLIQUES' is dedicated to invoicing "
                        "between public entities. Don't use it, otherwise "
                        "the invoice will be rejected."
                    )
                )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for service in self:
            name = f"[{service.code}] {service.name or '-'}"
            service.display_name = name

    _sql_constraints = [
        (
            "partner_code_uniq",
            "unique(partner_id, code)",
            "This Chorus service code already exists for that partner!",
        )
    ]

    @api.model
    def _name_search(self, name, domain=None, operator="ilike", limit=None, order=None):
        if domain is None:
            domain = []
        if name and operator == "ilike":
            ids = list(
                self._search(
                    [("code", "=ilike", name)] + domain, limit=limit, order=order
                )
            )
            if ids:
                return ids
            ids = list(
                self._search(
                    ["|", ("code", "ilike", name), ("name", "ilike", name)] + domain,
                    limit=limit,
                    order=order,
                )
            )
            if ids:
                return ids
        return super()._name_search(
            name, domain=domain, operator=operator, limit=limit, order=order
        )

    def _is_service_ok(self):
        if not self:
            return False
        if not self.active:
            return False
        if not self.name:
            return False
        return True

    def _api_consulter_service(self, api_params, session):
        assert self.chorus_identifier
        url_path = "structures/v1/consulter/service"
        payload = {
            "idStructure": self.partner_id.fr_chorus_identifier,
            "idService": self.chorus_identifier,
        }
        answer, session = self.env["res.company"]._chorus_post(
            api_params, url_path, payload, session=session
        )
        res = {}
        # from pprint import pprint
        # pprint(answer)
        if (
            answer.get("codeRetour") == 0
            and answer.get("parametres")
            and answer["parametres"].get("numeroEngagement")
        ):
            res["engagement_required"] = answer["parametres"]["numeroEngagement"]
        return (res, session)

    def service_update(self):
        company2api = {}
        raise_if_ko = self._context.get("chorus_raise_if_ko", True)
        services = []
        for service in self:
            partner = service.partner_id
            if not service.chorus_identifier:
                if raise_if_ko:
                    raise UserError(
                        _(
                            "Missing Chorus Identifier on service '%(service_name)s' "
                            "of partner '%(partner_name)s'."
                        )
                        % {
                            "service_name": service.display_name,
                            "partner_name": partner.display_name,
                        }
                    )
                else:
                    logger.warning(
                        "Skipping service %s of partner %s: missing "
                        "Chorus identifier",
                        service.display_name,
                        partner.display_name,
                    )
                    continue
            if not partner.fr_chorus_identifier:
                if raise_if_ko:
                    raise UserError(
                        _("Missing Chorus Identifier on partner %s.")
                        % partner.display_name
                    )
                else:
                    logger.warning(
                        "Skipping service %s of partner %s: missing Chorus "
                        "identifier on partner",
                        service.display_name,
                        partner.display_name,
                    )
                    continue
            company = partner.company_id or self.env.company
            if company not in company2api:
                api_params = company._chorus_get_api_params(raise_if_ko=raise_if_ko)
                if not api_params:
                    continue
                company2api[company] = api_params
            services.append(service)
        session = None
        for service in services:
            partner = service.partner_id
            company = partner.company_id or self.env.company
            api_params = company2api[company]
            (res, session) = service._api_consulter_service(api_params, session)
            if res:
                service.write({"engagement_required": res.get("engagement_required")})
