from stdnum.fr.siren import is_valid as siren_is_valid
from stdnum.fr.siret import is_valid as siret_is_valid

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Partner(models.Model):
    """Add the French official company identity numbers SIREN, NIC and SIRET"""

    _inherit = "res.partner"

    @api.model
    def _validate_siren(self, number, raise_if_not_valid=False) -> bool:
        valid = siren_is_valid(number)
        if raise_if_not_valid and not valid:
            raise ValidationError(_("SIREN '%s' is invalid.", number))
        return valid

    @api.model
    def _validate_nic(self, number, raise_if_not_valid=False) -> bool:
        valid = number.isdigit() and len(number) == 5
        if raise_if_not_valid and not valid:
            raise ValidationError(_("NIC '%s' is invalid.", number))
        return valid

    @api.model
    def _validate_siret(self, number, raise_if_not_valid=False) -> bool:
        # La Poste SIRET (except the head office) do not use the Luhn checksum
        # but the sum of digits must be  a multiple of 5
        #
        # This will not be necessary with python-stdnum > 1.17, but it's at the
        # moment unreleased.
        #
        # https://github.com/arthurdejong/python-stdnum/commit/73f5e3a86
        valid = False
        if number.startswith("356000000") and number != "35600000000048":
            valid = sum(map(int, number)) % 5 == 0
        else:
            valid = siret_is_valid(number)
        if raise_if_not_valid and not valid:
            raise ValidationError(_("SIRET '%s' is invalid.", number))
        return valid

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
                rec.siret = False

    def _inverse_siret(self):
        for rec in self:
            if rec.siret:
                if self._validate_siret(rec.siret):
                    rec.write({"siren": rec.siret[:9], "nic": rec.siret[9:]})
                elif self._validate_siren(rec.siret[:9]) and rec.siret[9:] == "*****":
                    rec.write({"siren": rec.siret[:9], "nic": False})
                else:
                    raise ValidationError(_("SIRET '%s' is invalid.") % rec.siret)
            else:
                rec.write({"siren": False, "nic": False})

    @api.constrains("siren", "nic")
    def _check_siret(self):
        """Check the SIREN's and NIC's keys (last digits)"""
        for rec in self:
            if rec.type == "contact" and rec.parent_id:
                continue
            if rec.nic:
                self._validate_nic(rec.nic, raise_if_not_valid=True)
            if rec.siren:
                self._validate_siren(rec.siren, raise_if_not_valid=True)
            # Check the NIC key (you need both SIREN and NIC to check it)
            if rec.siren and rec.nic:
                self._validate_siret(rec.siren + rec.nic, raise_if_not_valid=True)

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
        compute_sudo=True,
    )

    @api.depends("siren", "company_id")
    def _compute_same_siren_partner_id(self):
        # Inspired by same_vat_partner_id from 'base' module
        for partner in self:
            same_siren_partner_id = False
            if partner.siren and not partner.parent_id:
                domain = [
                    ("siren", "=", partner.siren),
                    ("parent_id", "=", False),
                ]
                if partner.company_id:
                    domain += [
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", partner.company_id.id),
                    ]
                # use _origin to deal with onchange()
                partner_id = partner._origin.id
                if partner_id:
                    domain.append(("id", "!=", partner_id))
                same_siren_partner_id = (
                    self.with_context(active_test=False).search(domain, limit=1)
                ).id or False
            partner.same_siren_partner_id = same_siren_partner_id
