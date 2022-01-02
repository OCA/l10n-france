# Copyright 2017-2021 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api

fr_states = {
    44: "res_country_state_alsace",
    75: "res_country_state_aquitaine",
    84: "res_country_state_auvergne",
    27: "res_country_state_bourgogne",
    53: "res_country_state_bretagne",
    24: "res_country_state_centre",
    94: "res_country_state_corse",
    11: "res_country_state_iledefrance",
    76: "res_country_state_languedocroussillon",
    32: "res_country_state_nordpasdecalais",
    28: "res_country_state_bassenormandie",
    52: "res_country_state_paysdelaloire",
    93: "res_country_state_provencealpescotedazur",
}

# This code is designed to avoid a problem in the following scenario:
# On a new database, the administrator executes these steps in this order:
# 1) installs base_location_geonames_import and run the geonames import wizard
#  for France
# -> it creates all the French regions (without xmlid)
# 2) installs l10n_fr_state (directly or when installing the module
#    for DEB l10n_fr_intrastat_product)
# -> it tries to create the French regions, but it fails due to the unicity
#  constraint unique(country_id, code) of res.country.state.


def create_fr_state_xmlid(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    fr_country = env.ref("base.fr")
    for region_code, xmlid in fr_states.items():
        regions = env["res.country.state"].search(
            [("code", "=", region_code), ("country_id", "=", fr_country.id)]
        )
        if regions:
            env["ir.model.data"].create(
                {
                    "name": xmlid,
                    "res_id": regions[0].id,
                    "module": "l10n_fr_state",
                    "model": "res.country.state",
                }
            )
    return
