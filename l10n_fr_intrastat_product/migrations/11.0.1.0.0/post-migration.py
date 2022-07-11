# Copyright 2021 ForgeFlow <http://www.forgeflow.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


def update_l10n_fr_intrastat_product_declaration_year(env):
    openupgrade.logged_query(
        env.cr, """
        UPDATE l10n_fr_intrastat_product_declaration
        SET year = {integer_year} || ''
        """.format(integer_year=openupgrade.get_legacy_name("year"))
    )


@openupgrade.migrate()
def migrate(env, version):
    update_l10n_fr_intrastat_product_declaration_year(env)
