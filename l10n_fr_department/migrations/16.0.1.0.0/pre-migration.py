# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if not openupgrade.column_exists(env.cr, "res_partner", "country_department_id"):
        openupgrade.rename_fields(
            env,
            [
                (
                    "res.partner",
                    "res_partner",
                    "department_id",
                    "country_department_id",
                ),
            ],
        )
