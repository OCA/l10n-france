# Copyright 2010-2022 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class IntrastatUnit(models.Model):
    _inherit = "intrastat.unit"

    fr_xml_label = fields.Char(
        string="Label for DEB",
        size=12,
        help="Label used in the XML file export of the French Intrastat "
        "Product Declaration for this supplementary unit of measure.",
    )
