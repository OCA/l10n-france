# Copyright 2016-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from lxml import etree

from odoo import SUPERUSER_ID, api
from odoo.tools import file_open

logger = logging.getLogger(__name__)


def set_unece_on_taxes(cr, registry):
    f = file_open("l10n_fr_account_tax_unece/data/account_tax_template.xml", "rb")
    xml_root = etree.parse(f)
    data = {}
    for record in xml_root.xpath("//record"):
        xmlid = record.attrib["id"]
        data[xmlid] = {}
        for xfield in record.xpath("field"):
            xfield_dict = xfield.attrib
            data[xmlid][xfield_dict["name"]] = xfield_dict.get("ref")
    logger.debug("set_unece_on_taxes data=%s", data)
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        companies = env["res.company"].search([])
        ato = env["account.tax"]
        imdo = env["ir.model.data"]
        for company in companies:
            logger.debug(
                "set_unece_on_taxes working on company %s ID %d",
                company.display_name,
                company.id,
            )
            if company.country_id and company.country_id != env.ref("base.fr"):
                continue
            taxes = ato.with_context(active_test=False).search(
                [("company_id", "=", company.id)]
            )
            for tax in taxes:
                xmlid_obj = imdo.search(
                    [
                        ("model", "=", "account.tax"),
                        ("module", "=", "l10n_fr"),
                        ("res_id", "=", tax.id),
                    ],
                    limit=1,
                )
                if xmlid_obj and xmlid_obj.name and len(xmlid_obj.name.split("_")) > 1:
                    # Remove the 'companyID_' prefix from XMLID of tax
                    xmlid_ori_end = "_".join(xmlid_obj.name.split("_")[1:])
                    xmlid_ori = "l10n_fr.%s" % xmlid_ori_end
                    if data.get(xmlid_ori):
                        vals = {}
                        for rfield, rxmlid in data[xmlid_ori].items():
                            if rxmlid:
                                vals[rfield] = env.ref(rxmlid).id
                        logger.debug(
                            "set_unece_on_taxes writing vals=%s on tax ID %d",
                            vals,
                            tax.id,
                        )
                        tax.write(vals)
    return
