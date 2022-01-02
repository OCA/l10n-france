# Copyright 2014-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def set_department_on_partner(cr, registry):
    """This post_install script is required because, when the module
    is installed, Odoo creates the column in the DB and compute the field
    and THEN it loads the file data/res_country_department_data.yml...
    So, when it computes the field on module installation, the
    departments are not available in the DB, so the department_id field
    on res.partner stays null. This post_install script fixes this."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    fr_countries = env["res.country"].search(
        [("code", "in", ("FR", "GP", "MQ", "GF", "RE", "YT"))]
    )
    partners = (
        env["res.partner"]
        .with_context(active_test=False)
        .search([("country_id", "in", fr_countries.ids)])
    )
    partners._compute_department()
    return
