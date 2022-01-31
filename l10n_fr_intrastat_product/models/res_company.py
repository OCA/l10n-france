# Copyright 2010-2022 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    # In France, the customs_accreditation ("numéro d'habilitation")
    # is 4 char long. But the spec of the XML file says it can go up
    # to 8... because other EU countries may have identifiers up to 8 chars
    # As this module only implement DEB for France, we use size=4
    fr_intrastat_accreditation = fields.Char(
        string="Customs accreditation identifier",
        size=4,
        help="Company identifier for Intrastat file export. " "Size : 4 characters.",
    )

    @api.constrains("intrastat_arrivals", "country_id")
    def check_fr_intrastat(self):
        for company in self:
            if company.country_id and company.country_id.code == "FR":
                if company.intrastat_arrivals == "standard":
                    raise ValidationError(
                        _("In France, Arrival DEB can only be Exempt or Extended.")
                    )
