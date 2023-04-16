# Copyright 2014-2020 Akretion France (http://www.akretion.com/)
# author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict
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
        datas = [(p.id, p.country_id.id, p.zip) for p in self]
        for dpt_id, partner_ids in self._prepare_compute_department(datas).items():
            self.browse(partner_ids).update({"department_id": dpt_id})

    @api.model
    def _prepare_compute_department(self, datas):
        rcdo = self.env["res.country.department"]
        fr_country_ids = self.env["res.country"]\
            .search([("code", "in", ("FR", "GP", "MQ", "GF", "RE", "YT"))]).ids

        map_partners = defaultdict(set)
        for partner_id, country_id, zipcode in datas:
            dpt_id = False
            if (
                country_id
                and zipcode
                and len(zipcode) == 5
                and country_id in fr_country_ids
            ):
                zipcode = zipcode.strip().replace(" ", "").rjust(5, "0")
                map_partners[(country_id, zipcode)].add(partner_id)
            else:
                map_partners[(False, False)].add(partner_id)

        res = defaultdict(set)
        for (country_id, zipcode), partner_ids in map_partners.items():
            dpt_id = False
            if zipcode and country_id:
                code = self._fr_zipcode_to_department_code(zipcode)
                dpt_id = rcdo.search(
                    [
                        ("code", "=", code),
                        ("country_id", "=", country_id),
                    ],
                    limit=1,
                ).id
            res[dpt_id].update(partner_ids)

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
