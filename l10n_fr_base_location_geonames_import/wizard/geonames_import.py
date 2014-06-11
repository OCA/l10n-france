# -*- encoding: utf-8 -*-
##############################################################################
#
#    l10n FR Base Location Geonames Import module for OpenERP
#    Copyright (C) 2014 Akretion (http://www.akretion.com/)
#    @author: Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import orm
from unidecode import unidecode


class better_zip_geonames_import(orm.TransientModel):
    _inherit = 'better.zip.geonames.import'

    def _prepare_better_zip(
            self, cr, uid, row, country_id, states, context=None):
        res = super(better_zip_geonames_import, self)._prepare_better_zip(
            cr, uid, row, country_id, states, context=context)
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
