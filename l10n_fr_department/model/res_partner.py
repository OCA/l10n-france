# Copyright 2014-2022 Akretion France (http://www.akretion.com/)
# author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    department_id = fields.Many2one(
        "res.country.department",
        compute="_compute_department",
        string="Department",
        store=True,
    )

    @api.depends("zip", "country_id", "country_id.code")
    # If a department code changes, it will have to be manually recomputed
    def _compute_department(self):
        rcdo = self.env["res.country.department"]
        fr_country_ids = (
            self.env["res.country"]
            .search([("code", "in", ("FR", "GP", "MQ", "GF", "RE", "YT"))])
            .ids
        )
        for partner in self:
            dpt_id = False
            zipcode = partner.zip
            if (
                partner.country_id
                and partner.country_id.id in fr_country_ids
                and zipcode
                and len(zipcode) == 5
            ):
                zipcode = partner.zip.strip().replace(" ", "").rjust(5, "0")
                code = self._fr_zipcode_to_department_code(zipcode)
                dpt = rcdo.search(
                    [
                        ("code", "=", code),
                        ("country_id", "in", fr_country_ids),
                    ],
                    limit=1,
                )
                dpt_id = dpt and dpt.id or False
            partner.department_id = dpt_id

    def _fr_zipcode_to_department_code(self, zipcode):
        code = zipcode[0:2]
        # https://fr.wikipedia.org/wiki/Liste_des_communes_de_France_dont_le_code_postal_ne_correspond_pas_au_d%C3%A9partement  # noqa
        special_zipcodes = {
            "42620": "03",
            "05110": "04",
            "05130": "04",
            "05160": "04",
            "06260": "04",
            "48250": "07",
            "43450": "15",
            "36260": "18",
            "33220": "24",
            "05700": "26",
            "73670": "38",
            "01410": "39",
            "01590": "39",
            "52100": "51",
            "21340": "71",
            "01200": "74",
            "13780": "83",
            "37160": "86",
            "94390": "91",
        }
        if zipcode in special_zipcodes:
            return special_zipcodes[zipcode]
        if code == "97":
            code = zipcode[0:3]
        elif code == "20":
            try:
                zipcode = int(zipcode)
            except ValueError:
                return "20"
            if 20000 <= zipcode < 20200:
                # Corse du Sud / 2A
                code = "2A"
            elif 20200 <= zipcode <= 20620:
                code = "2B"
            else:
                code = "20"
        return code
