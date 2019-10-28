# © 2019 Le Filament (https://le-filament.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    cedex = fields.Char("Cedex")

    @api.model
    def _address_fields(self):
        address_fields = super(ResPartner, self)._address_fields()
        address_fields.append('cedex')
        return address_fields
