import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

logger = logging.getLogger(__name__)


def _check_luhn(string):
    """Luhn test to check control keys

    Credits:
        http://rosettacode.org/wiki/Luhn_test_of_credit_card_numbers#Python
    """
    r = [int(ch) for ch in string][::-1]
    return (sum(r[0::2]) + sum(sum(divmod(d * 2, 10)) for d in r[1::2])) % 10 == 0


class Partner(models.Model):
    """Add the French official company identity numbers SIREN, NIC and SIRET"""

    _inherit = "res.partner"

    @api.depends("siren", "nic")
    def _compute_siret(self):
        """Concatenate the SIREN and NIC to form the SIRET"""
        for rec in self:
            if rec.siren:
                if rec.nic:
                    rec.siret = rec.siren + rec.nic
                else:
                    rec.siret = rec.siren + "*****"
            else:
                rec.siret = ""

    def _inverse_siret(self):
        for rec in self:
            siret = rec.siret and rec.siret.replace(" ", "") or False
            if siret and len(siret) == 14 and siret.isdigit():
                rec.siren = siret[:9]
                rec.nic = siret[9:]
            else:
                rec.siren = False
                rec.nic = False

    @api.constrains("siren", "nic")
    def _check_siret(self):
        """Check the SIREN's and NIC's keys (last digits)"""
        for rec in self:
            if rec.nic:
                # Check the NIC type and length
                if not rec.nic.isdecimal() or len(rec.nic) != 5:
                    raise ValidationError(
                        _(
                            "The NIC '%s' is incorrect: it must have "
                            "exactly 5 digits."
                        )
                        % rec.nic
                    )
            if rec.siren:
                # Check the SIREN type, length and key
                if not rec.siren.isdecimal() or len(rec.siren) != 9:
                    raise ValidationError(
                        _(
                            "The SIREN '%s' is incorrect: it must have "
                            "exactly 9 digits."
                        )
                        % rec.siren
                    )
                if not _check_luhn(rec.siren):
                    raise ValidationError(
                        _("The SIREN '%s' is invalid: the checksum is wrong.")
                        % rec.siren
                    )
                # Check the NIC key (you need both SIREN and NIC to check it)
                if rec.nic and not _check_luhn(rec.siren + rec.nic):
                    raise ValidationError(
                        _("The SIRET '%s%s' is invalid: " "the checksum is wrong.")
                        % (rec.siren, rec.nic)
                    )

    @api.model
    def _commercial_fields(self):
        # SIREN is the same for the whole company
        # NIC is different for each address
        res = super()._commercial_fields()
        res.append("siren")
        return res

    @api.model
    def _address_fields(self):
        res = super()._address_fields()
        res.append("nic")
        return res

    siren = fields.Char(
        string="SIREN",
        size=9,
        tracking=50,
        help="The SIREN number is the official identity "
        "number of the company in France. It composes "
        "the first 9 digits of the SIRET number.",
    )
    nic = fields.Char(
        string="NIC",
        size=5,
        tracking=51,
        help="The NIC number is the official rank number "
        "of this office in the company in France. It "
        "composes the last 5 digits of the SIRET "
        "number.",
    )
    # the original SIRET field is definied in l10n_fr
    # We add an inverse method to make it easier to copy/paste a SIRET
    # from an external source to the partner form view of Odoo
    siret = fields.Char(
        compute="_compute_siret",
        inverse="_inverse_siret",
        store=True,
        readonly=False,
        help="The SIRET number is the official identity number of this "
        "company's office in France. It is composed of the 9 digits "
        "of the SIREN number and the 5 digits of the NIC number, ie. "
        "14 digits.",
    )
    company_registry = fields.Char(
        string="Company Registry",
        size=64,
        help="The name of official registry where this company was declared.",
    )

    parent_is_company = fields.Boolean(
        related="parent_id.is_company", string="Parent is a Company"
    )
    same_siren_partner_id = fields.Many2one(
        "res.partner",
        compute="_compute_same_siren_partner_id",
        string="Partner with same SIREN",
    )

    @api.depends("siren", "company_id")
    def _compute_same_siren_partner_id(self):
        # Inspired by same_vat_partner_id from 'base' module
        for partner in self:
            same_siren_partner_id = False
            if partner.siren and not partner.parent_id:
                # use _origin to deal with onchange()
                partner_id = partner._origin.id
                domain = [
                    ("siren", "=", partner.siren),
                    ("company_id", "in", (False, partner.company_id.id)),
                    ("parent_id", "=", False),
                ]
                if partner_id:
                    domain += [
                        ("id", "!=", partner_id),
                        "!",
                        ("id", "child_of", partner_id),
                    ]
                same_siren_partner_id = (
                    self.with_context(active_test=False).sudo().search(domain, limit=1)
                )
            partner.same_siren_partner_id = same_siren_partner_id

    @api.model
    def _opendatasoft_fields_list(self):
        return [
            "datefermetureunitelegale",
            "datefermetureetablissement",
            "denominationunitelegale",
            "adresseetablissement",
            "codepostaletablissement",
            "libellecommuneetablissement",
            "siren",
            "nic",
            "codedepartementetablissement",
        ]

    @api.model
    def _opendatasoft_get_raw_data(
        self, query, raise_if_fail=False, exclude_dead=True, rows=10
    ):
        assert isinstance(query, str)
        assert isinstance(rows, int) and rows > 0
        url = "https://data.opendatasoft.com/api/records/1.0/search/"
        params = {
            "dataset": "economicref-france-sirene-v3@public",
            "q": query,
            "rows": rows,
            "fields": ",".join(self._opendatasoft_fields_list()),
        }
        if exclude_dead:
            params[
                "q"
            ] += " AND #null(datefermetureetablissement) AND #null(datefermetureunitelegale)"
        try:
            logger.info("Sending query to https://data.opendatasoft.com/api")
            logger.debug("url=%s params=%s", url, params)
            res = requests.get(url, params=params)
            if res.status_code in (200, 201):
                res_json = res.json()
                from pprint import pprint

                pprint(res_json)
                return res_json
            else:
                logger.warning(
                    "HTTP error %s returned by GET on data.opendatasoft.com/api",
                    res.status_code,
                )
                if raise_if_fail:
                    raise UserError(
                        _(
                            "The webservice data.opendatasoft.com "
                            "returned an HTTP error code %s."
                        )
                        % res.status_code
                    )
        except Exception as e:
            logger.warning("Failure in the GET request on data.opendatasoft.com: %s", e)
            if raise_if_fail:
                raise UserError(
                    _(
                        "Failure in the request on data.opendatasoft.com "
                        "to create or update partner from SIREN or SIRET. "
                        "Technical error: %s."
                    )
                    % e
                )
        return False

    @api.model
    def _opendatasoft_parse_record(self, raw_record):
        res = False
        if raw_record and isinstance(raw_record, dict):
            if raw_record.get("datefermetureunitelegale"):
                return res
            if raw_record.get("datefermetureetablissement"):
                return res
            res = {
                "name": raw_record.get("denominationunitelegale"),
                "street": raw_record.get("adresseetablissement"),
                "zip": raw_record.get("codepostaletablissement"),
                "city": raw_record.get("libellecommuneetablissement"),
                "siren": raw_record.get("siren"),
                "nic": raw_record.get("nic"),
            }
            if raw_record.get("codedepartementetablissement"):
                dpt_code = raw_record["codedepartementetablissement"]
                domtom2xmlid = {
                    "971": "gp",
                    "972": "mq",
                    "973": "gf",
                    "974": "re",
                    "975": "pm",  # Saint Pierre and Miquelon
                    "976": "yt",  # Mayotte
                    "977": "bl",  # Saint-Barthélemy
                    "978": "mf",  # Saint-Martin
                    "986": "wf",  # Wallis-et-Futuna
                    "987": "pf",  # Polynésie française
                    "988": "nc",  # Nouvelle calédonie
                }
                if len(dpt_code) == 2:
                    res["country_id"] = self.env.ref("base.fr").id
                elif dpt_code in domtom2xmlid:
                    country_xmlid = "base.%s" % domtom2xmlid[dpt_code]
                    res["country_id"] = self.env.ref(country_xmlid).id
            # set lang to French if installed
            fr_lang = self.env["res.lang"].search([("code", "=", "fr_FR")])
            if fr_lang:
                res["lang"] = "fr_FR"
        return res

    @api.model
    def _opendatasoft_get_first_result(self, query, raise_if_fail=False):
        res_json = self._opendatasoft_get_raw_data(query, raise_if_fail=raise_if_fail)
        if res_json and "records" in res_json:
            if len(res_json["records"]) > 0:
                raw_record = res_json["records"][0].get("fields")
                if raw_record:
                    return self._opendatasoft_parse_record(raw_record)
            else:
                logger.warning("The query on opendatasoft.com returned 0 records")
        return False

    @api.model
    def _opendatasoft_get_from_siren(self, siren):
        if siren and len(siren) == 9 and siren.isdigit() and _check_luhn(siren):
            vals = self._opendatasoft_get_first_result("siren:%s" % siren)
            if vals and vals.get("siren") == siren:
                return vals
        return False

    @api.model
    def _opendatasoft_get_from_siret(self, siret):
        if siret and len(siret) == 14 and siret.isdigit() and _check_luhn(siret):
            vals = self._opendatasoft_get_first_result("siret:%s" % siret)
            if vals and vals.get("siren") and vals.get("nic"):
                vals_siret = vals["siren"] + vals["nic"]
                if vals_siret == siret:
                    return vals
        return False

    @api.onchange("siren")
    def siren_onchange(self):
        if (
            self.siren
            and len(self.siren) == 9
            and self.siren.isdigit()
            and _check_luhn(self.siren)
            and not self.name
            and self.is_company
            and not self.parent_id
        ):
            if self.nic:
                # We only execute the query if the full SIRET is OK
                vals = False
                if (
                    len(self.nic) == 5
                    and self.nic.isdigit()
                    and _check_luhn(self.siren + self.nic)
                ):
                    siret = self.siren + self.nic
                    vals = self._opendatasoft_get_from_siret(siret)
            else:
                vals = self._opendatasoft_get_from_siren(self.siren)
            if vals:
                self.name = vals.get("name")
                self.street = vals.get("street")
                self.zip = vals.get("zip")
                self.city = vals.get("city")
                self.country_id = vals.get("country_id")
                if not self.nic:
                    self.nic = vals.get("nic")

    @api.onchange("siret")
    def siret_onchange(self):
        if (
            self.siret
            and len(self.siret) == 14
            and self.siret.isdigit()
            and _check_luhn(self.siret)
            and not self.name
            and self.is_company
            and not self.parent_id
        ):
            vals = self._opendatasoft_get_from_siret(self.siret)
            if vals:
                self.name = vals.get("name")
                self.street = vals.get("street")
                self.zip = vals.get("zip")
                self.city = vals.get("city")
                self.country_id = vals.get("country_id")
                if vals.get("lang"):
                    self.lang = vals["lang"]

    @api.onchange("name")
    def siret_or_siren_name_onchange(self):
        if (
            self.name
            and self.is_company
            and not self.parent_id
            and not self.siren
            and not self.nic
            and not self.siret
            and not self.street
            and not self.city
            and not self.zip
        ):
            name = self.name.replace(" ", "")
            if name and name.isdigit():
                vals = False
                if len(name) == 9 and _check_luhn(name):
                    vals = self._opendatasoft_get_from_siren(name)
                elif len(name) == 14 and _check_luhn(name):
                    vals = self._opendatasoft_get_from_siret(name)
                if vals:
                    self.name = vals.get("name")
                    self.street = vals.get("street")
                    self.zip = vals.get("zip")
                    self.city = vals.get("city")
                    self.country_id = vals.get("country_id")
                    self.siren = vals.get("siren")
                    self.nic = vals.get("nic")
                    if vals.get("lang"):
                        self.lang = vals["lang"]
