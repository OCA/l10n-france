# Copyright 2017-2020 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo.fields import Domain

logger = logging.getLogger(__name__)


def set_fr_company_intrastat(env):
    imdo = env["ir.model.data"]
    afpo = env["account.fiscal.position"]
    fr_id = env.ref("base.fr").id
    companies = env["res.company"].search(Domain("partner_id.country_id", "=", fr_id))
    fpdict = {
        "intraeub2b": "b2b",
        "intraeub2c": "b2c",
    }
    for company in companies:
        company.write(
            {
                "intrastat_transport_id": env.ref(
                    "intrastat_product.intrastat_transport_3"
                ).id,
                "intrastat_accessory_costs": True,
            }
        )
        logger.info(
            "Wrote intrastat_accessory_costs=True on company %s", company.display_name
        )
        fps = afpo.search(Domain("company_id", "=", company.id))
        for fp in fps:
            xmlid_rec = imdo.search(
                Domain("model", "=", "account.fiscal.position")
                & Domain("module", "=like", "l10n_fr%")
                & Domain("res_id", "=", fp.id),
                limit=1,
            )
            if xmlid_rec:
                for fp_type, intrastat in fpdict.items():
                    if xmlid_rec.name.endswith(fp_type):
                        logger.info(
                            "set_fr_company_intrastat writing intrastat=%s "
                            "on fiscal position ID %d",
                            intrastat,
                            fp.id,
                        )
                        vals = {"intrastat": intrastat}
                        fp.write(vals)
                        break
