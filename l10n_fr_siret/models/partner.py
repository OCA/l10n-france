from odoo import _, api, fields, models
from odoo.exceptions import UserError


# XXX: this is used for checking various codes such as credit card
# numbers: should it be moved to tools.py?
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

    @api.constrains("siren", "nic")
    def _check_siret(self):
        """Check the SIREN's and NIC's keys (last digits)"""
        for rec in self:
            if rec.nic:
                # Check the NIC type and length
                if not rec.nic.isdecimal() or len(rec.nic) != 5:
                    raise UserError(
                        _(
                            "The NIC '%s' is incorrect: it must have "
                            "exactly 5 digits."
                        )
                        % rec.nic
                    )
            if rec.siren:
                # Check the SIREN type, length and key
                if not rec.siren.isdecimal() or len(rec.siren) != 9:
                    raise UserError(
                        _(
                            "The SIREN '%s' is incorrect: it must have "
                            "exactly 9 digits."
                        )
                        % rec.siren
                    )
                if not _check_luhn(rec.siren):
                    raise UserError(
                        _("The SIREN '%s' is invalid: the checksum is wrong.")
                        % rec.siren
                    )
                # Check the NIC key (you need both SIREN and NIC to check it)
                if rec.nic and not _check_luhn(rec.siren + rec.nic):
                    raise UserError(
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
    siret = fields.Char(
        compute="_compute_siret",
        store=True,
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
