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
                active = False
            WHERE id in (
            SELECT "ir_ui_view".id FROM "ir_ui_view"
            WHERE (("ir_ui_view"."active" = true)
            AND (unaccent(COALESCE("ir_ui_view"."arch_db"->>'fr_FR',
            "ir_ui_view"."arch_db"->>'en_US')) ilike unaccent('%ecotaxe_classification_id%')))
            ORDER BY  "ir_ui_view"."priority" ASC  LIMIT 80
)
        """,
    )
    if not openupgrade.column_exists(
        env.cr, "account_ecotaxe_classification", "categ_id"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "account.ecotaxe.classification",
                    "accoun_tecotaxe_classification",
                    "account_ecotaxe_categ_id",
                    "categ_id",
                ),
            ],
        )
    if not openupgrade.column_exists(
        env.cr, "account_ecotaxe_classification", "sector_id"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "account.ecotaxe.classification",
                    "account_ecotaxe_classification",
                    "ecotaxe_sector_id",
                    "sector_id",
                ),
            ],
        )
    if not openupgrade.column_exists(
        env.cr, "account_ecotaxe_classification", "collector_id"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "account.ecotaxe.classification",
                    "account_ecotaxe_classification",
                    "ecotaxe_collector_id",
                    "collector_id",
                ),
            ],
        )
    if not openupgrade.column_exists(
        env.cr, "account_ecotaxe_classification", "product_status"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "account.ecotaxe.classification",
                    "account_ecotaxe_classification",
                    "ecotaxe_product_status",
                    "product_status",
                ),
            ],
        )
    if not openupgrade.column_exists(
        env.cr, "account_ecotaxe_classification", "supplier_status"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "account.ecotaxe.classification",
                    "account_ecotaxe_classification",
                    "ecotaxe_supplier_status",
                    "supplier_status",
                ),
            ],
        )
    if not openupgrade.column_exists(
        env.cr, "account_ecotaxe_classification", "emebi_code"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "account.ecotaxe.classification",
                    "account_ecotaxe_classification",
                    "ecotaxe_deb_code",
                    "emebi_code",
                ),
            ],
        )
    if not openupgrade.column_exists(
        env.cr, "account_ecotaxe_classification", "scale_code"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "account.ecotaxe.classification",
                    "account_ecotaxe_classification",
                    "ecotaxe_scale_code",
                    "scale_code",
                ),
            ],
        )
    if not openupgrade.column_exists(
        env.cr, "account_move_line_ecotaxe", "classification_id"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "account.move.line.ecotaxe",
                    "account_move_line_ecotaxe",
                    "ecotaxe_classification_id",
                    "classification_id",
                ),
            ],
        )
    if not openupgrade.column_exists(
        env.cr, "account_move_line_ecotaxe", "amount_unit"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "account.move.line.ecotaxe",
                    "account_move_line_ecotaxe",
                    "ecotaxe_amount_unit",
                    "amount_unit",
                ),
            ],
        )
    if not openupgrade.column_exists(
        env.cr, "account_move_line_ecotaxe", "amount_total"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "account.move.line.ecotaxe",
                    "account_move_line_ecotaxe",
                    "ecotaxe_amount_total",
                    "amount_total",
                ),
            ],
        )
    if not openupgrade.column_exists(
        env.cr, "account_move_line_ecotaxe", "force_amount_unit"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "account.move.line.ecotaxe",
                    "account_move_line_ecotaxe",
                    "force_ecotaxe_unit",
                    "force_amount_unit",
                ),
            ],
        )
    if not openupgrade.column_exists(
        env.cr, "ecotaxe_line_product", "classification_id"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "ecotaxe.line.product",
                    "ecotaxe_line_product",
                    "ecotaxe_classification_id",
                    "classification_id",
                ),
            ],
        )
    if not openupgrade.column_exists(env.cr, "ecotaxe_line_product", "force_amount"):
        openupgrade.rename_fields(
            env,
            [
                (
                    "ecotaxe.line.product",
                    "ecotaxe_line_product",
                    "force_ecotaxe_amount",
                    "force_amount",
                ),
            ],
        )
    if not openupgrade.column_exists(env.cr, "ecotaxe_line_product", "amount"):
        openupgrade.rename_fields(
            env,
            [
                (
                    "ecotaxe.line.product",
                    "ecotaxe_line_product",
                    "ecotaxe_amount",
                    "amount",
                ),
            ],
        )
