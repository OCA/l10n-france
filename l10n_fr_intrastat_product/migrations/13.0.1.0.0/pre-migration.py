# Copyright 2020 ForgeFlow <http://www.forgeflow.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
# Copied and adapted from the OCA module intrastat_product

from openupgradelib import openupgrade

_column_renames = {
    "l10n_fr_intrastat_product_declaration": [("month", None)],
    "l10n_fr_intrastat_product_computation_line": [("invoice_line_id", None)],
}


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_columns(env.cr, _column_renames)
