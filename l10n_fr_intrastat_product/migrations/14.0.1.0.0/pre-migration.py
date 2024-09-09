# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if openupgrade.table_exists(
        env.cr, "l10n_fr_intrastat_product_declaration"
    ) and openupgrade.column_exists(
        env.cr, "l10n_fr_intrastat_product_declaration", "type"
    ):
        openupgrade.logged_query(
            env.cr,
            "ALTER TABLE l10n_fr_intrastat_product_declaration RENAME type "
            "TO declaration_type",
        )
