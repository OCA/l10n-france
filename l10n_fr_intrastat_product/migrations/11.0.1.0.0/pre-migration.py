# Copyright 2021 ForgeFlow <http://www.forgeflow.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade

_column_renames = {
    "l10n_fr_intrastat_product_declaration": [("year", None)],
}


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_columns(env.cr, _column_renames)
