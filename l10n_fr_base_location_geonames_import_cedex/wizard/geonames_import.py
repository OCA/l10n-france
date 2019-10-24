# © 2019 Le Filament (https://le-filament.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class CityZipGeonamesImport(models.TransientModel):
    _inherit = 'city.zip.geonames.import'

    @api.model
    def _process_csv(self, parsed_csv):
        res = super(CityZipGeonamesImport, self)._process_csv(
            parsed_csv)
        if self.country_id.code in [
                'FR', 'RE', 'GP', 'MQ', 'GF', 'YT', 'BL', 'MF', 'PM',
                'PF', 'NC', 'WF', 'MC', 'AD']:
            zips = self.env['res.city.zip'].search([
                ('city_id.country_id', '=', self.country_id.id),
                ('name', 'ilike', ' CEDEX')])
            for zip_to_update in zips:
                position = zip_to_update['name'].rfind(' CEDEX')
                zip_to_update.cedex = zip_to_update.name[position:]
                zip_to_update.name = zip_to_update.name[0:position]

        return res
