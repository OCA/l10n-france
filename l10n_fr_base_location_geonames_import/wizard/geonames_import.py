# -*- coding: utf-8 -*-
# © 2014-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api
from unidecode import unidecode


class BetterZipGeonamesImport(models.TransientModel):
    _inherit = 'better.zip.geonames.import'

    @api.model
    def _prepare_better_zip(self, row, country):
        res = super(BetterZipGeonamesImport, self)._prepare_better_zip(
            row, country)
        if row[0] in [
                'FR', 'RE', 'GP', 'MQ', 'GF', 'YT', 'BL', 'MF', 'PM',
                'PF', 'NC', 'WF', 'MC', 'AD']:
            # Modify city and zip to comply with French postal standards
            res['city'] = unidecode(res['city']).upper().replace('-', ' ')
            # Try to comply with the standard that says res['city'] name is
            # 32 chars max
            if len(res['city']) > 32 and res['city'].startswith('SAINTE '):
                res['city'] = u'STE %s' % res['city'][7:]
            if len(res['city']) > 32 and res['city'].startswith('SAINT '):
                res['city'] = u'ST %s' % res['city'][6:]
            # Move CEDEX from zip to city field
            zipori = res['name']
            if ' CEDEX' in res['name']:
                position = res['name'].rfind(' CEDEX')
                res['name'] = res['name'][0:position]
                res['city'] = u'%s%s' % (res['city'], zipori[position:])
            rewrite_city_by_zip = {
                # Do not put the number of the arrondissement in the city name
                '69001': 'LYON',
                '69002': 'LYON',
                '69003': 'LYON',
                '69004': 'LYON',
                '69005': 'LYON',
                '69006': 'LYON',
                '69007': 'LYON',
                '69008': 'LYON',
                '69009': 'LYON',
                '13001': 'MARSEILLE',
                '13002': 'MARSEILLE',
                '13003': 'MARSEILLE',
                '13004': 'MARSEILLE',
                '13005': 'MARSEILLE',
                '13006': 'MARSEILLE',
                '13007': 'MARSEILLE',
                '13008': 'MARSEILLE',
                '13009': 'MARSEILLE',
                '13010': 'MARSEILLE',
                '13011': 'MARSEILLE',
                '13012': 'MARSEILLE',
                '13013': 'MARSEILLE',
                '13014': 'MARSEILLE',
                '13015': 'MARSEILLE',
                '13016': 'MARSEILLE',
                '75001': 'PARIS',
                '75002': 'PARIS',
                '75003': 'PARIS',
                '75004': 'PARIS',
                '75005': 'PARIS',
                '75006': 'PARIS',
                '75007': 'PARIS',
                '75008': 'PARIS',
                '75009': 'PARIS',
                '75010': 'PARIS',
                '75011': 'PARIS',
                '75012': 'PARIS',
                '75013': 'PARIS',
                '75014': 'PARIS',
                '75015': 'PARIS',
                '75016': 'PARIS',
                '75017': 'PARIS',
                '75018': 'PARIS',
                '75019': 'PARIS',
                '75020': 'PARIS',
            }
            if res['name'] in rewrite_city_by_zip:
                res['city'] = rewrite_city_by_zip[res['name']]
        return res
