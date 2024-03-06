# Copyright 2016-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

logger = logging.getLogger(__name__)


def set_unece_on_taxes(env):
    data = env["account.chart.template"]._fr_account_tax_unece_data()
    logger.debug("set_unece_on_taxes data=%s", data)
    companies = env["res.company"].search([])
    for company in companies:
        # country_id is NOT a stored field on res.company
        if company.country_id and company.country_id != env.ref("base.fr"):
            continue
        logger.debug(
            "set_unece_on_taxes working on company %s ID %d",
            company.display_name,
            company.id,
        )
        taxes = (
            env["account.tax"]
            .with_context(active_test=False)
            .search([("company_id", "=", company.id)])
        )
        for tax in taxes:
            xmlid_obj = env["ir.model.data"].search(
                [
                    ("model", "=", "account.tax"),
                    ("module", "=", "account"),
                    ("res_id", "=", tax.id),
                ],
                limit=1,
            )
            if xmlid_obj and xmlid_obj.name and len(xmlid_obj.name.split("_", 1)) == 2:
                # Remove the 'companyID_' prefix from XMLID of tax
                vals = data.get(xmlid_obj.name.split("_", 1)[1])
                if vals:
                    logger.debug(
                        "set_unece_on_taxes writing vals=%s on tax ID %d", vals, tax.id
                    )
                    tax.write(vals)
