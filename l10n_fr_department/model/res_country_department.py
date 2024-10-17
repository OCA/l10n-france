# Copyright 2013-2022 GRAP (http://www.grap.coop)
# Copyright 2015-2022 Akretion France (http://www.akretion.com)
# @author Sylvain LE GAL (https://twitter.com/legalsylvain)
# @author Alexis de Lattre (alexis.delattre@akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import api, fields, models


class ResCountryDepartment(models.Model):
    _description = "Department"
    _name = "res.country.department"
    _order = "country_id, code"

    state_id = fields.Many2one(
        "res.country.state",
        string="State",
        required=True,
        help="State related to the current department",
    )
    country_id = fields.Many2one(
        "res.country",
        related="state_id.country_id",
        string="Country",
        store=True,
        help="Country of the related state",
    )
    name = fields.Char(string="Department Name", size=128, required=True)
    code = fields.Char(
        string="Department Code",
        size=3,
        required=True,
        help="The department code (ISO 3166-2 codification)",
    )

    _sql_constraints = [
        (
            "code_uniq",
            "unique (code)",
            "You cannot have two departments with the same code!",
        )
    ]

    @api.depends("name", "code")
    def name_get(self):
        res = []
        for rec in self:
            dname = "{} ({})".format(rec.name, rec.code)
            res.append((rec.id, dname))
        return res

    @api.model
    def _name_search(
        self, name, args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        args = args or []

        if name:
            # Be sure name_search is symetric to name_get
            match = re.match(r"^(.*)\s\((.*)\)$", name)
            if match:
                dpt_name = match.group(1)
                dpt_code = match.group(2)
                args += [("code", operator, dpt_code), ("name", operator, dpt_name)]
            else:
                # Search on code and name
                if operator in ("not ilike", "!="):
                    bool_operator = "&"  # for negative comparators, use AND
                else:
                    bool_operator = "|"  # for positive comparators, use OR
                args += [
                    bool_operator,
                    ("code", operator, name),
                    ("name", operator, name),
                ]

        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
