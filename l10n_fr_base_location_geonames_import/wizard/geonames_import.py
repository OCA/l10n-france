# © 2019 Le Filament (https://le-filament.com).
# © 2014-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
from odoo import models, api
try:
    from unidecode import unidecode
except ImportError:
    unidecode = False


class CityZipGeonamesImport(models.TransientModel):
    _inherit = 'city.zip.geonames.import'

    @api.model
    def transform_city_name(self, city, country):
        res = super(CityZipGeonamesImport, self).transform_city_name(
            city, country)
        if country.code in [
                'FR', 'RE', 'GP', 'MQ', 'GF', 'YT', 'BL', 'MF', 'PM',
                'PF', 'NC', 'WF', 'MC', 'AD']:
            res = unidecode(res).upper().replace('-', ' ')
            # Try to comply with the standard that says res['city'] name is
            # 32 chars max
            if len(res) > 32 and res.startswith('SAINTE '):
                res = u'STE %s' % res[7:]
            if len(res) > 32 and res.startswith('SAINT '):
                res = u'ST %s' % res[6:]
            replace_arrondissement = re.compile('\s\d\d\Z')
            if re.search(replace_arrondissement, res):
                res = re.sub(replace_arrondissement, "", res)
        return res
