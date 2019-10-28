# © 2019 Le Filament (https://le-filament.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    cedex = fields.Char(compute='_compute_address', inverse='_inverse_cedex')

    def _get_company_address_fields(self, partner):
        address_fields = super(
            ResCompany, self)._get_company_address_fields(partner)
        address_fields['cedex'] = partner.cedex
        return address_fields

    def _inverse_cedex(self):
        for company in self:
            company.partner_id.cedex = company.cedex
