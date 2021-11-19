# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade
from psycopg2 import sql

_rename_columns = {
    "l10n_fr_intrastat_service_declaration": [("month", None), ("year", None),]
}


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_columns(env.cr, _rename_columns)
    openupgrade.add_fields(
        env,
        [
            (
                "start_date",
                "l10n.fr.intrastat.service.declaration",
                "l10n_fr_intrastat_service_declaration",
                "date",
                False,
                "l10n_fr_intrastat_service",
                False,
            )
        ],
    )

    month_col = openupgrade.get_legacy_name("month")
    year_col = openupgrade.get_legacy_name("year")
    sql_query = sql.SQL(
        """
    UPDATE l10n_fr_intrastat_service_declaration SET
    start_date = to_date(CONCAT({}, '-', {}, '-01'), 'YYYY-MM-DD')
    """
    ).format(sql.Identifier(year_col), sql.Identifier(month_col))
    openupgrade.logged_query(env.cr, sql_query)
