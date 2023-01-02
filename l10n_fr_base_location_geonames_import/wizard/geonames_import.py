# © 2014-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import models


class CityZipGeonamesImport(models.TransientModel):
    _inherit = "city.zip.geonames.import"

    def run_import(self):
        for country in self.country_ids:
            if country.code in [
                "FR",
                "RE",
                "GP",
                "MQ",
                "GF",
                "YT",
                "BL",
                "MF",
                "PM",
                "PF",
                "NC",
                "WF",
                "MC",
                "AD",
            ]:
                parsed_csv = self.get_and_parse_csv(country)
                for row in enumerate(parsed_csv):
                    # Do not put the number of the arrondissement in the city name
                    replace_arrondissement = re.compile(r"\s\d\d\Z")
                    if re.search(replace_arrondissement, row[2]):
                        row[2] = re.sub(replace_arrondissement, "", row[2])
                    # Move CEDEX from zip to city field
                    zipori = row[1]
                    if " CEDEX" in zipori:
                        position = zipori.rfind(" CEDEX")
                        row[1] = zipori[0:position]
                        row[2] = "%s%s" % (row[2], zipori[position:])
            self._process_csv(parsed_csv, country)
        return True
