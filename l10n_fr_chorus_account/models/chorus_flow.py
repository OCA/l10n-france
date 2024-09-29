# Copyright 2018-2020 Akretion France (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class ChorusFlow(models.Model):
    _name = "chorus.flow"
    _description = "Chorus Flow"
    _order = "id desc"

    name = fields.Char("Flow Ref", readonly=True, copy=False, required=True)
    date = fields.Date("Flow Date", readonly=True, copy=False, required=True)
    attachment_id = fields.Many2one(
        "ir.attachment", string="File Sent to Chorus", readonly=True, copy=False
    )
    status = fields.Char(string="Flow Status (raw value)", readonly=True, copy=False)
    status_display = fields.Char(
        compute="_compute_status_display", string="Flow Status", store=True
    )
    status_date = fields.Datetime(
        string="Last Status Update", readonly=True, copy=False
    )
    syntax = fields.Selection([], string="Flow Syntax", readonly=True, copy=False)
    notes = fields.Text(string="Notes", readonly=True, copy=False)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    invoice_identifiers = fields.Boolean(
        compute="_compute_invoice_identifiers", readonly=True, store=True
    )
    initial_invoice_ids = fields.Many2many(
        "account.move",
        "chorus_flow_initial_account_move_rel",
        "chorus_flow_id",
        "move_id",
        string="Initial Invoices",
        help="Invoices in the flow before potential rejections",
    )
    invoice_ids = fields.One2many(
        "account.move",
        "chorus_flow_id",
        string="Invoices",
        readonly=True,
        help="Invoices in the flow after potential rejections",
    )
    chorus_response = fields.Text()

    @api.depends("status")
    def _compute_status_display(self):
        for flow in self:
            if flow.status and flow.status.startswith("IN_") and len(flow.status) > 3:
                status_display = flow.status[3:].replace("_", " ")
            else:
                status_display = flow.status
            flow.status_display = status_display

    @api.depends("invoice_ids.chorus_identifier")
    def _compute_invoice_identifiers(self):
        for flow in self:
            flow.invoice_identifiers = all(
                [inv.chorus_identifier for inv in flow.invoice_ids]
            )

    @api.depends("name", "status_display")
    def name_get(self):
        res = []
        for flow in self:
            name = flow.name
            if flow.status_display:
                status = flow.status_display
                name = "{} ({})".format(name, status)
            res.append((flow.id, name))
        return res

    @api.model
    def syntax_odoo2chorus(self):
        return {}

    def chorus_api_consulter_cr(self, api_params, session=None):
        self.ensure_one()
        payload = {
            "numeroFluxDepot": self.name,
        }
        # The webservice 'consulterCR' is broken for Factur-X (1/5/2018)
        # So I switch to 'consulterCRDetaille' which works fine for all formats
        answer, session = self.env["res.company"].chorus_post(
            api_params, "transverses/v1/consulterCRDetaille", payload, session=session
        )
        res = {}
        if answer:
            notes = ""
            if answer.get("listeErreurDP") and isinstance(
                answer["listeErreurDP"], list
            ):
                i = 0
                for error in answer["listeErreurDP"]:
                    i += 1
                    notes += (
                        "Erreur %d :\n"
                        "  Identifiant fournisseur : %s\n"
                        "  Identifiant destinataire : %s\n"
                        "  Ref facture : %s\n"
                        "  Libellé erreur : %s\n"
                        % (
                            i,
                            error.get("identifiantFournisseur"),
                            error.get("identifiantDestinataire"),
                            error.get("numeroDP"),
                            error.get("libelleErreurDP"),
                        )
                    )
            res = {
                "status": answer.get("etatCourantDepotFlux"),
                "notes": notes or answer.get("libelle"),
                "chorus_response": json.dumps(answer),
            }
        return (res, session)

    def update_flow_status(self):
        """Called by a button on the flow or by cron"""
        logger.info("Start to update chorus flow status")
        company2api = {}
        raise_if_ko = self._context.get("chorus_raise_if_ko", True)
        flows = []
        for flow in self:
            company = flow.company_id
            if company not in company2api:
                api_params = company.chorus_get_api_params(raise_if_ko=raise_if_ko)
                if not api_params:
                    continue
                company2api[company] = api_params
            flows.append(flow)
        session = None
        for flow in flows:
            api_params = company2api[flow.company_id]
            flow_vals, session = flow.chorus_api_consulter_cr(
                api_params, session=session
            )
            if flow_vals:
                flow_vals["status_date"] = fields.Datetime.now()
                flow.write(flow_vals)
        logger.info("End of the update of chorus flow status")

    def chorus_api_rechercher_fournisseur(self, api_params, session=None):
        self.ensure_one()
        url_path = "factures/v1/rechercher/fournisseur"
        payload = {
            "numeroFluxDepot": self.name,
            "rechercheFactureParFournisseur": {
                "nbResultatsParPage": 10,
                "pageResultatDemandee": 0,
            },
        }
        invnum2chorus = {}
        while True:
            payload["rechercheFactureParFournisseur"]["pageResultatDemandee"] += 1
            answer, session = self.env["res.company"].chorus_post(
                api_params, url_path, payload
            )
            # key = odoo invoice number, value = {} to write on odoo invoice
            if answer.get("listeFactures") and isinstance(
                answer["listeFactures"], list
            ):
                for cinv in answer["listeFactures"]:
                    if cinv.get("numeroFacture") and cinv.get("identifiantFactureCPP"):
                        invnum2chorus[cinv["numeroFacture"]] = {
                            "chorus_identifier": cinv["identifiantFactureCPP"],
                        }
                        if cinv.get("statut"):
                            invnum2chorus[cinv["numeroFacture"]].update(
                                {
                                    "chorus_status": cinv["statut"],
                                    "chorus_status_date": fields.Datetime.now(),
                                }
                            )
                if (
                    payload["rechercheFactureParFournisseur"]["pageResultatDemandee"]
                    >= answer["parametresRetour"]["pages"]
                ):
                    break
            else:
                break
        return invnum2chorus, session

    def get_invoice_identifiers(self):
        """Called by a button or cron"""
        logger.info("Start to get chorus invoice identifiers")
        company2api = {}
        raise_if_ko = self._context.get("chorus_raise_if_ko", True)
        flows = []
        for flow in self:
            if flow.status not in ("IN_INTEGRE", "IN_INTEGRE_PARTIEL"):
                if raise_if_ko:
                    raise UserError(
                        _(
                            "On flow %s, the status is not 'INTEGRE' "
                            "nor 'INTEGRE PARTIEL'."
                        )
                        % (flow.name, flow.status)
                    )
                logger.warning(
                    "Skipping flow %s: chorus flow status should be "
                    "IN_INTEGRE or IN_INTEGRE_PARTIEL but current value is %s",
                    flow.name,
                    flow.status,
                )
                continue
            if flow.invoice_identifiers:
                if raise_if_ko:
                    raise UserError(
                        _(
                            "The Chorus Invoice Identifiers are already set "
                            "for flow %s"
                        )
                        % flow.name
                    )
                logger.warning(
                    "Skipping flow %s: chorus identifiers already set", flow.name
                )
                continue
            company = flow.company_id
            if company not in company2api:
                api_params = company.chorus_get_api_params(raise_if_ko=raise_if_ko)
                if not api_params:
                    continue
                company2api[company] = api_params
            flows.append(flow)
        session = None
        for flow in flows:
            api_params = company2api[flow.company_id]
            invnum2chorus, session = flow.chorus_api_rechercher_fournisseur(
                api_params, session=session
            )
            if invnum2chorus:
                for inv in flow.invoice_ids:
                    if inv.name in invnum2chorus:
                        inv.write(invnum2chorus[inv.name])
            flow._process_rejected_invoices()
        logger.info("End of the retrieval of chorus invoice identifiers")

    def _process_rejected_invoices(self):
        self.ensure_one()
        if self.chorus_response:
            inv2errors = {
                error["numeroDP"]: error.get("libelleErreurDP")
                for error in json.loads(self.chorus_response)["listeErreurDP"]
            }
        else:
            inv2errors = {}
        for invoice in self.invoice_ids:
            if not invoice.chorus_identifier:
                # All the infoice without any chorus_identifier are considered as
                # rejected.
                # Most of the time chorus have sucessfully returned the right error
                # message in the response when calling flow update state
                # but sometime it doesn't ;) so missing invoice are we always rejected,
                # invoice without error message will have a generic error message
                invoice._chorus_set_as_rejected(
                    inv2errors.get(
                        invoice.name, _("Internal Chorus Error, please Resumit")
                    )
                )

    @api.model
    def chorus_cron(self):
        self = self.with_context(chorus_raise_if_ko=False)
        logger.info("Start Chorus flow cron")
        to_update_flows = self.search(
            [("status", "not in", ("IN_REJETE", "IN_INTEGRE", "IN_INTEGRE_PARTIEL"))]
        )
        to_update_flows.update_flow_status()
        get_identifiers_flows = self.search(
            [
                ("status", "in", ("IN_INTEGRE", "IN_INTEGRE_PARTIEL")),
                ("invoice_identifiers", "=", False),
            ]
        )
        get_identifiers_flows.get_invoice_identifiers()
        invoices_update_invoice_status = self.env["account.move"].search(
            [
                ("state", "=", "posted"),
                ("move_type", "in", ("out_invoice", "out_refund")),
                ("transmit_method_code", "=", "fr-chorus"),
                ("chorus_identifier", "!=", False),
                ("chorus_status", "not in", ("MANDATEE", "MISE_EN_PAIEMENT")),
            ]
        )
        invoices_update_invoice_status.chorus_update_invoice_status()
        logger.info("End Chorus flow cron")
