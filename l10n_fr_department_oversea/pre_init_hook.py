# Copyright 2017-2022 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.l10n_fr_state.pre_init_hook import generic_create_state_xmlid

# This code is designed to avoid a problem in the following scenario:
# On a new database, the administrator executes these steps in this order:
# 1) installs base_address_extended_geonames_import and run the geonames import wizard
#  for one of the French DOMs
# -> it creates the corresponding French regions (without xmlid)
# 2) installs l10n_fr_department_oversea
# -> it tries to create the res.country.state, but it fails due to the unicity
#  constraint unique(country_id, code) of res.country.state.


def create_fr_oversea_state_xmlid(env):
    generic_create_state_xmlid(
        env, "l10n_fr_department_oversea", "data/res_country_state.xml"
    )
