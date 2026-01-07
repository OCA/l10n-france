# Copyright 2014-2022 Akretion France (http://www.akretion.com/)
# author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import api, fields, models

try:
    from unidecode import unidecode
except ImportError:
    unidecode = None
FR_SPECIAL_ZIPCODES = {
    "42620": {"laval": "03"},
    "05110": {"claret": "04", "curbans": "04"},
    "05130": {"piegut": "04", "venterol": "04"},
    "05160": {"pontis": "04"},
    "06260": {"rochette": "04", "pierre": "04"},
    "48250": {"laveyrune": "07"},
    "43450": {"leyvaux": "15"},
    "33220": {"fougueyrolles": "24", "ponchapt": "24"},
    "05700": {"villebois": "26"},
    "01410": {"lajoux": "39"},
    "01590": {"chancia": "39", "lavancia": "39"},
    "52100": {"eulien": "51", "sapignicourt": "51"},
    "21340": {"change": "71"},
    "01200": {"eloise": "74"},
    "13780": {"riboux": "83"},
    "37160": {"buxeuil": "86"},
    "94390": {"paray": "91"},
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Warning: The OCA module 'partner_contact_department'
    # from https://github.com/OCA/partner-contact
    # adds a field 'department_id' on res.partner
    # So we chose a more specific field name: country_department_id
    country_department_id = fields.Many2one(
        "res.country.department",
        compute="_compute_country_department",
        string="Country Department",
        store=True,
    )

    @api.depends("zip", "city", "country_id")
    # If a department code changes, it will have to be manually recomputed
    def _compute_country_department(self):
        fr_dom_countries_codes = ("FR", "GP", "MQ", "GF", "RE", "YT")
        fr_dom_countries_domain = [("code", "in", fr_dom_countries_codes)]
        fr_dom_countries_sr = self.env["res.country"].search_read(
            fr_dom_countries_domain, ["id"]
        )
        fr_dom_countries_ids = [country["id"] for country in fr_dom_countries_sr]

        # Retrieve all available departments by normalized department zip code
        department_sr = self.env["res.country.department"].search_read(
            [("country_id", "in", fr_dom_countries_ids)], ["code"]
        )
        department_code2id = {dpt["code"]: dpt["id"] for dpt in department_sr}

        # Shortcut: if no department is set for the given zip codes, make a
        # single assignment for the whole recordset with the null value (this
        # will surely happen the first time the module is installed: field is
        # computed before loading ``res.country.department`` records via
        # .xml file)
        if not department_code2id:
            self.country_department_id = False
        # Else: group departments by zip code, assign them to the grouped
        # partners according to their common zip code
        else:
            dpt_code2partner_ids = defaultdict(list)
            for partner in self:
                if partner.country_id.id in fr_dom_countries_ids and partner.zip:
                    dpt_code = self._fr_zipcode_city_to_department_code(
                        partner.zip, partner.city
                    )
                    dpt_code2partner_ids[dpt_code].append(partner.id)
                else:
                    dpt_code2partner_ids[None].append(partner.id)
            for dpt_code, partner_ids in dpt_code2partner_ids.items():
                self.browse(partner_ids).country_department_id = department_code2id.get(
                    dpt_code
                )

    @api.model
    def _fr_zipcode_city_to_department_code(self, zipcode, city):
        # https://fr.wikipedia.org/wiki/Liste_des_communes_de_France_dont_le_code_postal_ne_correspond_pas_au_d%C3%A9partement  # noqa
        zipcode = "".join(x for x in zipcode if not x.isspace())
        if len(zipcode) != 5:
            return None
        if city and zipcode in FR_SPECIAL_ZIPCODES:
            city = unidecode(city).lower()
            for city_keyword, dpt_code in FR_SPECIAL_ZIPCODES[zipcode].items():
                if city_keyword in city:
                    return dpt_code
        code = zipcode[0:2]
        # La Réunion
        if code == "97":
            code = zipcode[0:3]
            # Le Port
            if code == "978":
                code = "974"
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
