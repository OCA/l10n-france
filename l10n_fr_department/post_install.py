# Copyright 2014-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from collections import defaultdict
from odoo import SUPERUSER_ID, api


def set_department_on_partner(cr, registry):
    """This post_install script is required because, when the module
    is installed, Odoo creates the column in the DB and compute the field
    and THEN it loads the file data/res_country_department_data.yml...
    So, when it computes the field on module installation, the
    departments are not available in the DB, so the department_id field
    on res.partner stays null. This post_install script fixes this."""
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        fr_countries = env["res.country"].search(
            [("code", "in", ("FR", "GP", "MQ", "GF", "RE", "YT"))]
        )
        rcdo = env["res.country.department"]
        map_department = dict((d["code"], d["id"]) for d in rcdo.search_read(
            [("country_id", "in", fr_countries.ids)], ["code", "id"]))

        partners = [(p["id"], p["zip"])
                    for p in env["res.partner"]
                    .with_context(active_test=False)
                    .search_read([("country_id", "in", fr_countries.ids),
                                  ("zip", '!=', False)],
                                 ["id", "zip"])
                    ]

        map_partners = defaultdict(set)

        for partner_id, zipcode in partners:
            if len(zipcode) == 5:
                map_partners[zipcode].add(partner_id)

        for zipcode, partner_ids in map_partners.items():
            zipcode = zipcode.strip().replace(" ", "").rjust(5, "0")
            code = env['res.partner']._fr_zipcode_to_department_code(zipcode)
            dpt_id = map_department.get(code, False)
            if not dpt_id:
                continue
            for sub_ids in env.cr.split_for_in_conditions(partner_ids):
                env.cr.execute(
                    "UPDATE res_partner SET department_id=%s WHERE id IN %s",
                    (dpt_id, tuple(sub_ids)),
                )
