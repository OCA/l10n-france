# -*- coding: utf-8 -*-
# © 2010-2017 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class IntrastatUnit(models.Model):
    _inherit = "intrastat.unit"

    fr_xml_label = fields.Char(
        string='Label for DEB', size=12,
        help="Label used in the XML file export of the French Intrastat "
        "Product Declaration for this unit of measure.")
