# Copyright 2020 ForgeFlow <http://www.forgeflow.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# Copied and adapted from the OCA module intrastat_product

from openupgradelib import openupgrade  # pylint: disable=W7936

_months = [
    (1, "01"),
    (2, "02"),
    (3, "03"),
    (4, "04"),
    (5, "05"),
    (6, "06"),
    (7, "07"),
    (8, "08"),
    (9, "09"),
    (10, "10"),
    (11, "11"),
    (12, "12"),
]


def map_intrastat_product_declaration_month(env):
    openupgrade.map_values(
        env.cr,
        openupgrade.get_legacy_name("month"),
        "month",
        _months,
        table="l10n_fr_intrastat_product_declaration",
    )


def update_invoice_relation_fields(env):
    if openupgrade.table_exists(env.cr, "account_invoice_line"):
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE l10n_fr_intrastat_product_computation_line lfipcl
            SET invoice_line_id = aml.id
            FROM account_invoice_line ail
            JOIN account_move_line aml ON aml.old_invoice_line_id = ail.id
            WHERE lfipcl.%(old_line_id)s = ail.id"""
            % {"old_line_id": openupgrade.get_legacy_name("invoice_line_id")},
        )


@openupgrade.migrate()
def migrate(env, version):
    map_intrastat_product_declaration_month(env)
    update_invoice_relation_fields(env)
