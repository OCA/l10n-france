# Copyright 2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

from odoo.addons.l10n_fr_department.model.res_partner import FR_SPECIAL_ZIPCODES


@openupgrade.migrate()
def migrate(env, version):
    fr_country_id = env.ref("base.fr").id
    partners = env["res.partner"].search(
        [
            ("country_id", "=", fr_country_id),
            ("zip", "in", tuple(FR_SPECIAL_ZIPCODES.keys())),
        ]
    )
    partners._compute_country_department()
