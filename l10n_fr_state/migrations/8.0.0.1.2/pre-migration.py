# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Akretion (http://www.akretion.com/)
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


def migrate(cr, version):
    if not version:
        return

    # key : region XMLID - value : new name
    new_names = {
        'res_country_state_alsace': u'Grand Est',
        'res_country_state_aquitaine': u'Nouvelle Aquitaine',
        'res_country_state_languedocroussillon': u'Occitanie',
        'res_country_state_nordpasdecalais': u'Hauts-de-France',
        }

    for xmlid, new_name in new_names.iteritems():
        cr.execute("""
            SELECT res_id from ir_model_data where model='res.country.state'
            AND module='l10n_fr_state' AND name=%s
            """, (xmlid, ))
        state_id = cr.fetchall()
        cr.execute(
            "UPDATE res_country_state SET name=%s WHERE id=%s",
            (new_name, state_id))
