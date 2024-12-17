# Copyright 2024 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        "UPDATE account_tax SET country_id=res_partner.country_id "
        "FROM res_partner, res_company "
        "WHERE account_tax.company_id=res_company.id AND "
        "res_company.partner_id=res_partner.id AND "
        "res_partner.country_id IS NOT NULL AND "
        "account_tax.country_id IS NULL",
    )
