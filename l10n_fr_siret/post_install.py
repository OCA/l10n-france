# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import logging

from stdnum.fr.siret import is_valid

from odoo import SUPERUSER_ID, api

logger = logging.getLogger(__name__)


def set_siren_nic(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    partners = (
        env["res.partner"]
        .with_context(active_test=False)
        .search([("siret", "!=", False), ("parent_id", "=", False)])
    )
    for partner in partners:
        if is_valid(partner.siret):
            logger.info("Setting SIREN and NIC on partner %s", partner.display_name)
            partner.write({"siret": partner.siret})
        else:
            logger.warning(
                "Remove SIRET %s on partner %s because checksum is wrong",
                partner.siret,
                partner.display_name,
            )
            partner.write({"siret": False})
