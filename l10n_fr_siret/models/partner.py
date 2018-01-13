from odoo import models, fields, api, _
from odoo.exceptions import UserError


# XXX: this is used for checking various codes such as credit card
# numbers: should it be moved to tools.py?
def _check_luhn(string):
    """Luhn test to check control keys

    Credits:
        http://rosettacode.org/wiki/Luhn_test_of_credit_card_numbers#Python
    """
    r = [int(ch) for ch in string][::-1]
    return (sum(r[0::2]) + sum(sum(divmod(d * 2, 10))
                               for d in r[1::2])) % 10 == 0


class Partner(models.Model):
    """Add the French official company identity numbers SIREN, NIC and SIRET"""
    _inherit = 'res.partner'

    @api.multi
    @api.depends('siren', 'nic')
    def _compute_siret(self):
        """Concatenate the SIREN and NIC to form the SIRET"""
        for rec in self:
            if rec.siren:
                if rec.nic:
                    rec.siret = rec.siren + rec.nic
                else:
                    rec.siret = rec.siren + '*****'
            else:
                rec.siret = ''

    @api.constrains('siren', 'nic')
    def _check_siret(self):
        """Check the SIREN's and NIC's keys (last digits)"""
        for rec in self:
            if rec.nic:
                # Check the NIC type and length
                if not rec.nic.isdecimal() or len(rec.nic) != 5:
                    raise UserError(
                        _("The NIC '%s' is incorrect: it must have "
                            "exactly 5 digits.")
                        % rec.nic)
            if rec.siren:
                # Check the SIREN type, length and key
                if not rec.siren.isdecimal() or len(rec.siren) != 9:
                    raise UserError(
                        _("The SIREN '%s' is incorrect: it must have "
                            "exactly 9 digits.") % rec.siren)
                if not _check_luhn(rec.siren):
                    raise UserError(
                        _("The SIREN '%s' is invalid: the checksum is wrong.")
                        % rec.siren)
                # Check the NIC key (you need both SIREN and NIC to check it)
                if rec.nic and not _check_luhn(rec.siren + rec.nic):
                    return UserError(
                        _("The SIRET '%s%s' is invalid: "
                          "the checksum is wrong.")
                        % (rec.siren, rec.nic))


    def _commercial_fields(self):
        res = super(Partner, self)._commercial_fields()
        res += ['siren', 'nic']
        return res

    siren = fields.Char(
        string='SIREN', size=9, track_visibility='onchange',
        help="The SIREN number is the official identity "
        "number of the company in France. It composes "
        "the first 9 digits of the SIRET number.")
    nic = fields.Char(
        string='NIC', size=5, track_visibility='onchange',
        help="The NIC number is the official rank number "
        "of this office in the company in France. It "
        "composes the last 5 digits of the SIRET "
        "number.")
    siret = fields.Char(
        compute='_compute_siret', string='SIRET', size=14, store=True,
        help="The SIRET number is the official identity number of this "
        "company's office in France. It is composed of the 9 digits "
        "of the SIREN number and the 5 digits of the NIC number, ie. "
        "14 digits.")
    company_registry = fields.Char(
        string='Company Registry', size=64,
        help="The name of official registry where this company was declared.")
