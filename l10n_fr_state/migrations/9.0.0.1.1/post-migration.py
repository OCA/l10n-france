# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import pooler, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return

    pool = pooler.get_pool(cr.dbname)
    imdo = pool['ir.model.data']
    rcso = pool['res.country.state']
    # key : region XMLID - value : new name
    new_names = {
        'res_country_state_alsace': u'Grand Est',
        'res_country_state_aquitaine': u'Nouvelle Aquitaine',
        'res_country_state_languedocroussillon': u'Occitanie',
        'res_country_state_nordpasdecalais': u'Hauts-de-France',
        }

    for xmlid, new_name in new_names.iteritems():
        state_id = imdo.xmlid_to_res_id(
            cr, SUPERUSER_ID, 'l10n_fr_state.' + xmlid)
        if state_id:
            rcso.write(cr, SUPERUSER_ID, state_id, {'name': new_name})
