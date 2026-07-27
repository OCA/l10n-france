# Copyright 2021-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import logging

from stdnum.fr.siren import is_valid as siren_is_valid
from stdnum.fr.siret import is_valid as siret_is_valid

logger = logging.getLogger(__name__)


def set_siren_nic(env):
    logger.info("Starting data migration of fields siret/siren/nic on res.partner")
    # Fix demo data a the beginning, to avoid the logger.warning that break tests
    demo_fr_company = env.ref("base.partner_demo_company_fr", raise_if_not_found=False)
    if demo_fr_company:
        demo_fr_company.write({"siret": "74694878500017"})
        logger.info(
            "Changed SIRET on demo partner FR Company to be consistent with VAT"
        )
    partners = (
        env["res.partner"]
        .with_context(active_test=False)
        .search([("siret", "!=", False), ("parent_id", "=", False)])
    )
    for partner in partners:
        ini_siret = "".join(x for x in partner.siret if not x.isspace())
        ini_vat = (
            partner.vat and "".join(x for x in partner.vat if not x.isspace()) or False
        )
        if ini_vat and ini_vat.startswith("FR") and not ini_vat.endswith(ini_siret[:9]):
            siren = ini_vat[-9:]
            logger.warning(
                "Removed SIRET %s on partner %s because it is inconsistent with "
                "VAT %s. Keep only SIREN %s",
                ini_siret,
                partner.display_name,
                ini_vat,
                siren,
            )
            partner.write({"siren": siren, "nic": False})
        elif len(ini_siret) == 14 and siret_is_valid(ini_siret):
            logger.debug("Setting SIREN and NIC on partner %s", partner.display_name)
            partner.write({"siret": ini_siret})
        elif len(ini_siret) == 9 and siren_is_valid(ini_siret):
            logger.debug("Setting SIREN on partner %s", partner.display_name)
            partner.write({"siren": ini_siret})
        elif len(ini_siret) > 9 and siren_is_valid(ini_siret[:9]):
            logger.info(
                "Setting SIREN %s on partner %s. Wrong additional chars ignored "
                "(bad initial SIRET was %s)",
                ini_siret[:9],
                partner.display_name,
                ini_siret,
            )
            partner.write({"siren": ini_siret[:9]})
        else:
            logger.warning(
                "Remove SIRET %s on partner %s (bad length and/or checksum, "
                "doesn't start with valid SIREN)",
                ini_siret,
                partner.display_name,
            )
            partner.write({"siret": False})
    logger.info("End of data migration of fields siret/siren/nic on res.partner")
