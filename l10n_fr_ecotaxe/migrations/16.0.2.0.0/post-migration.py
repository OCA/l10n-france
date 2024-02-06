# Copyright 2024 Akretion France (http://www.akretion.com/)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # Due to the bug of update module we need to deactivate view
    openupgrade.logged_query(
        env.cr,
        """
            UPDATE ir_ui_view set
                active = True
            WHERE  id in (
            SELECT "ir_ui_view".id FROM "ir_ui_view"
            WHERE (("ir_ui_view"."active" = False)
            AND (unaccent(COALESCE("ir_ui_view"."arch_db"->>'fr_FR',
             "ir_ui_view"."arch_db"->>'en_US')) ilike unaccent('%classification_id%')))
)
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
            UPDATE ir_ui_view set
                active = False WHERE id in (
            SELECT "ir_ui_view".id FROM "ir_ui_view"
            WHERE (("ir_ui_view"."active" = true)
            AND (unaccent(COALESCE("ir_ui_view"."arch_db"->>'fr_FR',
            "ir_ui_view"."arch_db"->>'en_US')) ilike unaccent('%ecotaxe_classification_id%')))
            ORDER BY  "ir_ui_view"."priority" ASC  LIMIT 80)
        """,
    )
