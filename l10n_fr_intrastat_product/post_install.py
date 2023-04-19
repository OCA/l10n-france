# Copyright 2017-2022 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api

logger = logging.getLogger(__name__)


def set_fr_company_intrastat(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    imdo = env["ir.model.data"]
    afpo = env["account.fiscal.position"]
    fr_id = env.ref("base.fr").id
    companies = env["res.company"].search([("partner_id.country_id", "=", fr_id)])
    for company in companies:
        company.intrastat_accessory_costs = True

        fps = afpo.search([("company_id", "=", company.id)])
        for fp in fps:
            xmlid_rec = imdo.search(
                [
                    ("model", "=", "account.fiscal.position"),
                    ("module", "=", "l10n_fr"),
                    ("res_id", "=", fp.id),
                    ("name", "=like", "%_fiscal_position_template_intraeub2b"),
                ],
                limit=1,
            )
            if xmlid_rec:
                logger.debug(
                    "set_fr_company_intrastat writing intrastat=True "
                    "on fiscal position ID %d",
                    fp.id,
                )
                fp.write({"intrastat": companies._compute_intrastat()})
