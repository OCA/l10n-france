# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class IntrastatFrRegime(models.Model):
    _name = "intrastat.fr.regime"
    _description = "Intrastat: Code regime for France"
    _order = "code"

    code = fields.Char(size=2, required=True, readonly=True)
    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    description = fields.Text()
    is_fiscal_only = fields.Boolean(
        string="Is fiscal only ?",
        readonly=True,
    )
    fiscal_value_multiplier = fields.Integer(
        readonly=True,
        help="Used to compute the total fiscal value of the declaration.",
    )
    declaration_type = fields.Selection(
        [
            ("arrivals", "Arrivals"),
            ("dispatches", "Dispatches"),
        ],
        readonly=True,
    )

    # replace the native SQL constraint of the intrastat_product module
    _sql_constraints = [
        ("code_unique", "unique(code)", "This code regime already exists.")
    ]

    @api.depends("code", "name")
    def name_get(self):
        res = []
        for rec in self:
            name = "%s. %s" % (rec.code, rec.name)
            res.append((rec.id, name))
        return res
