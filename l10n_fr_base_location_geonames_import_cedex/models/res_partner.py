# © 2019 Le Filament (<http://www.le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('zip_id')
    def _onchange_zip_id(self):
        res = super(ResPartner, self)._onchange_zip_id()
        if self.zip_id:
            vals = {
                'cedex': self.zip_id.cedex,
            }
            self.update(vals)
        return res
