# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from lxml import etree

from odoo import SUPERUSER_ID, api
from odoo.tools import file_open

logger = logging.getLogger(__name__)


# Countries data is provided in the base module with noupdate="1"
# That's why we need this post-install script
def set_fr_cog(cr, registry):
    f = file_open("l10n_fr_cog/data/country.xml", "rb")
    xml_root = etree.parse(f)
    data = {}
    for record in xml_root.xpath("//record"):
        xmlid = record.attrib["id"]
        data[xmlid] = {}
        for xfield in record.xpath("field"):
            if xfield.attrib and xfield.attrib.get("name") == "fr_cog":
                data[xmlid] = int(xfield.text)
    logger.debug("set_fr_cog data=%s", data)
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        for xmlid, fr_cog in data.items():
            country = env.ref(xmlid)
            country.fr_cog = fr_cog
            logger.debug(
                "Country ID %d xmlid %s updated with fr_cog=%d",
                country.id,
                xmlid,
                fr_cog,
            )
    return
