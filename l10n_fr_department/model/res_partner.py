# Copyright 2014-2022 Akretion France (http://www.akretion.com/)
# author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.cache import ormcache
from odoo.tools.misc import groupby


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Warning: The OCA module 'partner_contact_department'
    # from https://github.com/OCA/partner-contact
    # adds a field 'department_id' on res.partner
    # So we chose a more specific field name: country_department_id
    country_department_id = fields.Many2one(
        "res.country.department",
        compute="_compute_country_department",
        string="Department",
        store=True,
    )

    @api.depends("zip", "country_id", "country_id.code")
    # If a department code changes, it will have to be manually recomputed
    def _compute_country_department(self):
        def _get_zipcode(partner) -> str:
            if partner.country_id not in fr_countries:
                return ""
            partner_zip = partner.zip
            if not partner_zip:
                return ""
            partner_zip = partner_zip.strip().replace(" ", "").rjust(5, "0")
            return partner_zip if len(partner_zip) == 5 else ""

        fr_countries_codes = ("FR", "GP", "MQ", "GF", "RE", "YT")
        fr_countries_domain = [("code", "in", fr_countries_codes)]
        fr_countries = self.env["res.country"].search(fr_countries_domain)

        # Group partners by zip code
        partners_by_zipcode = dict(groupby(self, key=_get_zipcode))

        # Retrieve all available departments by normalized department zip code
        department_obj = self.env["res.country.department"]
        zip2dep = self._fr_zipcode_to_department_code
        department_codes = {zip2dep(c) for c in partners_by_zipcode if c}
        departments = department_obj
        if department_codes:
            departments_domain = [
                ("code", "in", tuple(department_codes)),
                ("country_id", "in", fr_countries.ids),
            ]
            departments = department_obj.search(departments_domain)

        # Shortcut: if no department is set for the given zip codes, make a
        # single assignment for the whole recordset with the null value (this
        # will surely happen the first time the module is installed: field is
        # computed before loading ``res.country.department`` records via
        # .xml file)
        if not departments:
            self.country_department_id = False
        # Else: group departments by zip code, assign them to the grouped
        # partners according to their common zip code
        else:
            departments_by_code = dict(groupby(departments, key=lambda d: d.code))
            for zipcode, partner_list in partners_by_zipcode.items():
                department = department_obj
                if zipcode:
                    dep_code = zip2dep(zipcode)
                    if dep_code in departments_by_code:
                        department = departments_by_code[dep_code][0]
                self.browse().concat(*partner_list).country_department_id = department

    @api.model
    @ormcache("zipcode")
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
