# -*- coding: utf-8 -*-
# © 2011-2017 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    intrastat_fiscal_representative_id = fields.Many2one(
        'res.partner', string="EU fiscal representative",
        domain=[('parent_id', '=', False)],
        help="If this partner is located outside the EU but you "
        "deliver the goods inside the UE, the partner needs to "
        "have a fiscal representative with a VAT number inside the EU. "
        "In this scenario, the VAT number of the fiscal representative "
        "will be used for the Intrastat Product report (DEB).")

    # Copy field 'intrastat_fiscal_representative' from company partners
    # to their contacts
    @api.model
    def _commercial_fields(self):
        res = super(ResPartner, self)._commercial_fields()
        res.append('intrastat_fiscal_representative_id')
        return res

    @api.constrains('intrastat_fiscal_representative_id')
    def _check_fiscal_representative(self):
        """The Fiscal rep. must be based in the same country as our
        company or in an intrastat country"""
        for partner in self:
            rep = partner.intrastat_fiscal_representative_id
            if rep:
                if not rep.country_id:
                    raise ValidationError(_(
                        "The fiscal representative '%s' of partner '%s' "
                        "must have a country.")
                        % (rep.name, partner.name))
                if not rep.country_id.intrastat:
                    raise ValidationError(_(
                        "The fiscal representative '%s' of partner '%s' "
                        "must be based in an EU country.")
                        % (rep.name, partner.name))
                if not rep.vat:
                    raise ValidationError(_(
                        "The fiscal representative '%s' of partner '%s' "
                        "must have a VAT number.")
                        % (rep.name, partner.name))
