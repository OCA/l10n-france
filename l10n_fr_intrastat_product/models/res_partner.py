# Copyright 2011-2022 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    intrastat_fiscal_representative_id = fields.Many2one(
        "res.partner",
        string="EU fiscal representative",
        domain=[("parent_id", "=", False)],
        help="If this partner is located outside the EU but you "
        "deliver the goods inside the UE, the partner needs to "
        "have a fiscal representative with a VAT number inside the EU. "
        "In this scenario, the VAT number of the fiscal representative "
        "will be used for the Intrastat Product report (DEB).",
    )

    @api.constrains("intrastat_fiscal_representative_id")
    def _check_fiscal_representative(self):
        """The Fiscal rep. must be based in the same country as our
        company or in an intrastat country"""
        eu_countries = self.env.ref("base.europe").country_ids
        for partner in self:
            rep = partner.intrastat_fiscal_representative_id
            if rep:
                if not rep.country_id:
                    raise ValidationError(
                        _(
                            "The fiscal representative '{fiscal_rep}' of partner '{partner}' "
                            "must have a country."
                        ).format(
                            fiscal_rep=rep.display_name, partner=partner.display_name
                        )
                    )
                if rep.country_id not in eu_countries:
                    raise ValidationError(
                        _(
                            "The fiscal representative '{fiscal_rep}' of partner '{partner}' "
                            "must be based in an EU country."
                        ).format(
                            fiscal_rep=rep.display_name, partner=partner.display_name
                        )
                    )
                if not rep.vat:
                    raise ValidationError(
                        _(
                            "The fiscal representative '{fiscal_rep}' of partner '{partner}' "
                            "must have a VAT number."
                        ).format(
                            fiscal_rep=rep.display_name, partner=partner.display_name
                        )
                    )
