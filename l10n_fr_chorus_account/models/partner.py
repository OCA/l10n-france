# Copyright 2017-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # On commercial partner only
    fr_chorus_required = fields.Selection(
        [
            ("none", "None"),
            ("service", "Service"),
            ("engagement", "Engagement"),
            # better to use a bad English translation of the French word!
            ("service_or_engagement", "Service or Engagement"),
            ("service_and_engagement", "Service and Engagement"),
        ],
        string="Info Required for Chorus",
        tracking=True,
    )
    fr_chorus_identifier = fields.Integer("Chorus Identifier", readonly=True)
    fr_chorus_service_count = fields.Integer(
        compute="_compute_fr_chorus_service_count",
        readonly=True,
        string="Number of Chorus Services",
    )
    # On contact partner only
    fr_chorus_service_id = fields.Many2one(
        "chorus.partner.service",
        string="Chorus Service",
        ondelete="restrict",
        tracking=True,
    )
    # On parent partner only
    fr_chorus_service_ids = fields.One2many(
        "chorus.partner.service", "partner_id", string="Chorus Services"
    )

    def _compute_fr_chorus_service_count(self):
        rg_res = self.env["chorus.partner.service"].read_group(
            [("partner_id", "in", self.ids)], ["partner_id"], ["partner_id"]
        )
        mapped_data = {
            x["partner_id"][0]: x["partner_id_count"] for x in rg_res
        }
        for partner in self:
            partner.fr_chorus_service_count = mapped_data.get(partner.id, 0)

    @api.constrains("fr_chorus_service_id", "name", "parent_id")
    def check_fr_chorus_service(self):
        for partner in self:
            if partner.fr_chorus_service_id:
                if not partner.parent_id:
                    raise ValidationError(
                        _(
                            "Chorus service codes can only be set on contacts, "
                            "not on parent partners. Chorus service code '%s' has "
                            "been set on partner %s that has no parent."
                        )
                        % (partner.fr_chorus_service_id.code, partner.display_name)
                    )
                if not partner.name:
                    raise ValidationError(
                        _(
                            "Contacts with a Chorus service code should have a "
                            "name. The Chorus service code '%s' has been set on "
                            "a contact without a name."
                        )
                        % partner.fr_chorus_service_id.code
                    )
                if (
                    partner.fr_chorus_service_id.partner_id
                    != partner.commercial_partner_id
                ):
                    raise ValidationError(
                        _(
                            "The Chorus Service '%s' configured on contact '%s' "
                            "is attached to another partner (%s)."
                        )
                        % (
                            partner.fr_chorus_service_id.display_name,
                            partner.display_name,
                            partner.fr_chorus_service_id.partner_id.display_name,
                        )
                    )

    def fr_chorus_api_structures_rechercher(self, api_params, session=None):
        url_path = "structures/v1/rechercher"
        payload = {
            "structure": {
                "identifiantStructure": self.siret,
                "typeIdentifiantStructure": "SIRET",
            },
        }
        answer, session = self.env["res.company"].chorus_post(
            api_params, url_path, payload, session=session
        )
        res = False
        # from pprint import pprint
        # pprint(answer)
        if (
            answer.get("listeStructures")
            and len(answer["listeStructures"]) == 1
            and answer["listeStructures"][0].get("idStructureCPP")
        ):
            res = answer["listeStructures"][0]["idStructureCPP"]
        return (res, session)

    def fr_chorus_identifier_get(self):
        company2api = {}
        raise_if_ko = self._context.get("chorus_raise_if_ko", True)
        partners = []
        for partner in self.filtered(lambda p: not p.fr_chorus_identifier):
            if partner.parent_id:
                if raise_if_ko:
                    raise UserError(
                        _("Cannot get Chorus Identifier on a contact (%s)")
                        % partner.display_name
                    )
                else:
                    logger.warning(
                        "Skipping partner %s: not a contact", partner.display_name
                    )
                    continue
            if not partner.nic or not partner.siren:
                if raise_if_ko:
                    raise UserError(
                        _("Missing SIRET on partner %s") % partner.display_name
                    )
                else:
                    logger.warning(
                        "Skipping partner %s: missing SIRET", partner.display_name
                    )
                    continue
            if (
                partner.customer_invoice_transmit_method_code != "fr-chorus"
                and not self.env.context.get("get_company_identifier")
            ):
                if raise_if_ko:
                    raise UserError(
                        _(
                            "On partner %s, the invoice transmit method "
                            "is not set to Chorus"
                        )
                        % partner.display_name
                    )
                else:
                    logger.warning(
                        "Skipping partner %s: invoice transmit method "
                        "not set to fr-chorus",
                        partner.display_name,
                    )
                    continue
            company = partner.company_id or self.env.user.company_id
            if company not in company2api:
                api_params = company.chorus_get_api_params(raise_if_ko=raise_if_ko)
                if not api_params:
                    continue
                company2api[company] = api_params
            partners.append(partner)
        session = None
        for partner in partners:
            company = partner.company_id or self.env.user.company_id
            api_params = company2api[company]
            (res, session) = partner.fr_chorus_api_structures_rechercher(
                api_params, session
            )
            if res:
                partner.write({"fr_chorus_identifier": res})
            else:
                if raise_if_ko:
                    raise UserError(
                        _(
                            "No entity found in Chorus corresponding to SIRET %s. "
                            "The detailed error is written in Odoo server logs."
                        )
                        % partner.siret
                    )
                else:
                    logger.warning(
                        "Skipping partner %s: No entity found in Chorus "
                        "corresponding to SIRET %s.",
                        partner.display_name,
                        partner.siret,
                    )

    def fr_chorus_api_structures_consulter(self, api_params, session):
        url_path = "structures/v1/consulter"
        payload = {"idStructureCPP": self.fr_chorus_identifier}
        answer, session = self.env["res.company"].chorus_post(
            api_params, url_path, payload, session=session
        )
        res = False
        # from pprint import pprint
        # pprint(answer)
        if answer.get("parametres"):
            if answer["parametres"].get("gestionNumeroEJOuCodeService"):
                res = "service_or_engagement"
            elif answer["parametres"].get("codeServiceDoitEtreRenseigne") and answer[
                "parametres"
            ].get("numeroEJDoitEtreRenseigne"):
                res = "service_and_engagement"
            elif answer["parametres"].get("codeServiceDoitEtreRenseigne"):
                res = "service"
            elif answer["parametres"].get("numeroEJDoitEtreRenseigne"):
                res = "engagement"
            else:
                res = "none"
        return (res, session)

    def fr_chorus_required_get(self):
        company2api = {}
        raise_if_ko = self._context.get("chorus_raise_if_ko", True)
        partners = []
        for partner in self:
            if not partner.fr_chorus_identifier:
                if raise_if_ko:
                    raise UserError(
                        _("Missing Chorus Identifier on partner '%s'.")
                        % partner.display_name
                    )
                else:
                    logger.warning(
                        "Skipping partner %s: missing chorus identifier",
                        partner.display_name,
                    )
                    continue
            company = partner.company_id or self.env.user.company_id
            if company not in company2api:
                api_params = company.chorus_get_api_params(raise_if_ko=raise_if_ko)
                if not api_params:
                    continue
                company2api[company] = api_params
            partners.append(partner)
        session = None
        for partner in partners:
            company = partner.company_id or self.env.user.company_id
            api_params = company2api[company]
            (res, session) = partner.fr_chorus_api_structures_consulter(
                api_params, session
            )
            if res:
                partner.write({"fr_chorus_required": res})

    def fr_chorus_api_rechercher_services(self, api_params, session):
        url_path = "structures/v1/rechercher/services"
        payload = {
            "idStructure": self.fr_chorus_identifier,
            "parametresRechercherServicesStructure": {"nbResultatsParPage": 10000},
        }
        answer, session = self.env["res.company"].chorus_post(
            api_params, url_path, payload, session=session
        )
        res = {}
        # from pprint import pprint
        # pprint(answer)
        if (
            answer.get("codeRetour") == 0
            and answer.get("listeServices")
            and isinstance(answer["listeServices"], list)
        ):
            for srv in answer["listeServices"]:
                if (
                    srv.get("codeService")
                    and srv["codeService"] != "FACTURES_PUBLIQUES"
                ):
                    res[srv["codeService"]] = {
                        "name": srv.get("libelleService"),
                        "active": srv.get("estActif"),
                        "chorus_identifier": int(srv.get("idService")),
                    }
        # answer: {u'codeRetour': 0,
        # u'libelle': u'TRA_MSG_00.000',
        # u'listeServices': [{u'codeService': u'XX',
        #                     u'dateDbtService': u'2016-10-25 17:42',
        #                     u'dateFinService': u'2050-12-31 00:00',
        #                     u'estActif': True,
        #                     u'idService': 27946199,
        #                     u'libelleService': u'CODE SERVICE INCONNU'},
        #                    {u'codeService': u'W9',
        #                     u'dateDbtService': u'2016-10-25 17:40',
        #                     u'dateFinService': u'2050-12-31 00:00',
        #                     u'estActif': True,
        #                     u'idService': 27946194,
        #                     u'libelleService': u'Murielle ANDRE'},
        # [...]
        # u'parametresRetour': {u'nbResultatsParPage': 10,
        #                       u'pageCourante': 1,
        #                       u'pages': 22,
        #                       u'total': 218}}
        return (res, session)

    def fr_chorus_services_get(self):
        company2api = {}
        raise_if_ko = self._context.get("chorus_raise_if_ko", True)
        partners = self.env["res.partner"]
        for partner in self:
            if not partner.fr_chorus_identifier:
                if raise_if_ko:
                    raise UserError(
                        _("Missing Chorus Identifier on partner %s.")
                        % partner.display_name
                    )
                else:
                    logger.warning(
                        "Skipping partner %s: missing Chorus identifier",
                        partner.display_name,
                    )
                    continue
            if not partner.fr_chorus_required:
                if raise_if_ko:
                    raise UserError(
                        _("Missing Info Required for Chorus on partner %s.")
                        % partner.display_name
                    )
                else:
                    logger.warning(
                        "Skipping partner %s: fr_chorus_required not set",
                        partner.display_name,
                    )
                    continue
            company = partner.company_id or self.env.user.company_id
            if company not in company2api:
                api_params = company.chorus_get_api_params(raise_if_ko=raise_if_ko)
                if not api_params:
                    continue
                company2api[company] = api_params
            partners |= partner

        session = None
        cpso = self.env["chorus.partner.service"]
        partner_existing_res = {}
        existing_srvs = cpso.with_context(active_test=False).search_read(
            [("partner_id", "in", partners.ids)],
            ["partner_id", "code", "name", "chorus_identifier", "active"],
        )
        for existing_srv in existing_srvs:
            partner_id = existing_srv["partner_id"][0]
            if partner_id not in partner_existing_res:
                partner_existing_res[partner_id] = {}

            partner_existing_res[partner_id][existing_srv["code"]] = {
                "id": existing_srv["id"],
                "name": existing_srv["name"],
                "active": existing_srv["active"],
                "chorus_identifier": existing_srv["chorus_identifier"],
            }

        # We don't filter on fr_chorus_required in 'service', ...
        # because we can have Chorus partners that have services
        # but the service information is not required
        for partner in partners:
            company = partner.company_id or self.env.user.company_id
            api_params = company2api[company]
            (res, session) = partner.fr_chorus_api_rechercher_services(
                api_params, session
            )
            if res:
                # from pprint import pprint
                # pprint(res)
                logger.info(
                    "Starting to update Chorus services of partner %s ID %d",
                    partner.display_name,
                    partner.id,
                )
                existing_res = partner_existing_res.get(partner.id, {})
                # pprint(existing_res)
                # I match on code instead of chorus_identifier
                # because Services can be created manually at the beginning
                # before we start using the API
                for (ccode, cdata) in res.items():
                    if existing_res.get(ccode):
                        existing_p = existing_res[ccode]
                        if (
                            existing_p.get("name") != cdata.get("name")
                            or existing_p.get("chorus_identifier")
                            != cdata.get("chorus_identifier")
                            or existing_p.get("active") != cdata.get("active")
                        ):
                            partner_service = cpso.browse(existing_p["id"])
                            partner_service.write(cdata)
                            logger.info(
                                "Chorus partner service ID %d with Chorus "
                                "code %s updated",
                                existing_p["id"],
                                ccode,
                            )
                        else:
                            logger.info(
                                "Chorus partner service ID %d with Chorus "
                                "code %s kept unchanged",
                                existing_p["id"],
                                ccode,
                            )
                    else:
                        partner_service = cpso.create(
                            {
                                "partner_id": partner.id,
                                "code": ccode,
                                "name": cdata["name"],
                                "active": cdata["active"],
                                "chorus_identifier": cdata["chorus_identifier"],
                            }
                        )
                        logger.info(
                            "Chorus partner service with Chorus code %s "
                            "created (ID %d)",
                            ccode,
                            partner_service.id,
                        )

    def fr_chorus_identifier_and_required_button(self):
        self.fr_chorus_identifier_get()
        self.fr_chorus_required_get()
        self.fr_chorus_services_get()
        for partner in self:
            partner.fr_chorus_service_ids.service_update()
        return

    @api.model
    def chorus_cron(self):
        logger.info("Start Chorus partner cron")
        to_update_partners = self.search(
            [
                ("parent_id", "=", False),
                ("customer_invoice_transmit_method_code", "=", "fr-chorus"),
                ("siren", "!=", False),
                ("nic", "!=", False),
            ]
        )
        to_update_partners.with_context(
            chorus_raise_if_ko=False
        ).fr_chorus_identifier_and_required_button()
        logger.info("End Chorus partner cron")

    def chorus_service_ok(self):
        # Method used upon SO or invoice validation
        self.ensure_one()
        if (
            self.parent_id
            and self.name
            and self.fr_chorus_service_id
            and self.fr_chorus_service_id.active
        ):
            return True
        else:
            return False
