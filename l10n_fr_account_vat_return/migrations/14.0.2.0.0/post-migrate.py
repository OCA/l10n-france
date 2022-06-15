# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from openupgradelib import openupgrade

logger = logging.getLogger("OpenUpgrade")


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        "SELECT id FROM res_partner WHERE %(partner_old_col)s IS true"
        % {"partner_old_col": openupgrade.get_legacy_name("supplier_vat_on_payment")},
    )
    partner_ids = [x[0] for x in env.cr.fetchall()]
    afpo = env["account.fiscal.position"]
    rco = env["res.company"]
    move_old_col = openupgrade.get_legacy_name("in_vat_on_payment")
    for company in rco.search([]):
        company_id = company.id
        fr_fps = afpo.search(
            [("company_id", "=", company_id), ("fr_vat_type", "=", "france")]
        )
        if not fr_fps:
            logger.info(
                "Company %s doesn't have any fiscal position with "
                "fr_vat_type=france",
                company.name,
            )
            continue
        new_fp = afpo.create(
            {
                "name": "France Fournisseur TVA sur encaiss.",
                "fr_vat_type": "france_vendor_vat_on_payment",
                "company_id": company_id,
            }
        )
        logger.info(
            "New fiscal position france_vendor_vat_on_payment created in company %s",
            company.name,
        )
        partners_to_update = (
            env["res.partner"].with_company(company_id).browse(partner_ids)
        )
        for partner in partners_to_update:
            if (
                not partner.property_account_position_id
                or partner.property_account_position_id.id in fr_fps.ids
            ):
                partner.write({"property_account_position_id": new_fp.id})
                logger.info(
                    "Partner %s now has the new fiscal position "
                    "france_vendor_vat_on_payment in company %s",
                    partner.display_name,
                    company.name,
                )
        openupgrade.logged_query(
            env.cr,
            "UPDATE account_move SET fiscal_position_id=%%s "
            "WHERE %(move_old_col)s IS true AND "
            "company_id=%%s AND "
            "(fiscal_position_id IS null OR fiscal_position_id IN %%s)"
            % {"move_old_col": move_old_col},
            args=(new_fp.id, company_id, tuple(fr_fps.ids)),
        )
