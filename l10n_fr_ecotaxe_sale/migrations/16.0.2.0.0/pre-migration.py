# Copyright 2024 Akretion France (http://www.akretion.com/)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if not openupgrade.column_exists(
        env.cr, "sale_order_line_ecotaxe", "classification_id"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "sale.order.line.ecotaxe",
                    "sale_order_line_ecotaxe",
                    "ecotaxe_classification_id",
                    "classification_id",
                ),
            ],
        )
    if not openupgrade.column_exists(env.cr, "sale_order_line_ecotaxe", "amount_unit"):
        openupgrade.rename_fields(
            env,
            [
                (
                    "sale.order.line.ecotaxe",
                    "sale_order_line_ecotaxe",
                    "ecotaxe_amount_unit",
                    "amount_unit",
                ),
            ],
        )
    if not openupgrade.column_exists(env.cr, "sale_order_line_ecotaxe", "amount_total"):
        openupgrade.rename_fields(
            env,
            [
                (
                    "sale.order.line.ecotaxe",
                    "sale_order_line_ecotaxe",
                    "ecotaxe_amount_total",
                    "amount_total",
                ),
            ],
        )
    if not openupgrade.column_exists(
        env.cr, "sale_order_line_ecotaxe", "force_amount_unit"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "sale.order.line.ecotaxe",
                    "sale_order_line_ecotaxe",
                    "force_ecotaxe_unit",
                    "force_amount_unit",
                ),
            ],
        )
