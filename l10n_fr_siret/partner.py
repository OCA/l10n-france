# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2011 Numérigraphe SARL
#    Copyright (C) 2014 Akretion France SARL
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import Warning


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

    @api.one
    @api.depends('siren', 'nic')
    def _get_siret(self):
        """Concatenate the SIREN and NIC to form the SIRET"""
        if self.siren:
            if self.nic:
                self.siret = self.siren + self.nic
            else:
                self.siret = self.siren + '*****'
        else:
            self.siret = ''

    @api.one
    @api.constrains('siren', 'nic')
    def _check_siret(self):
        """Check the SIREN's and NIC's keys (last digits)"""
        if self.nic:
            # Check the NIC type and length
            if not self.nic.isdecimal() or len(self.nic) != 5:
                raise Warning(
                    _("The NIC '%s' is incorrect: it must be have "
                        "exactly 5 digits.")
                    % self.nic)
        if self.siren:
            # Check the SIREN type, length and key
            if not self.siren.isdecimal() or len(self.siren) != 9:
                raise Warning(
                    _("The SIREN '%s' is incorrect: it must have "
                        "exactly 9 digits.") % self.siren)
            if not _check_luhn(self.siren):
                raise Warning(
                    _("The SIREN '%s' is invalid: the checksum is wrong.")
                    % self.siren)
            # Check the NIC key (you need both SIREN and NIC to check it)
            if self.nic and not _check_luhn(self.siren + self.nic):
                return Warning(
                    _("The SIRET '%s%s' is invalid: the checksum is wrong.")
                    % (self.siren, self.nic))

    @api.model
    def _commercial_fields(self):
        res = super(Partner, self)._commercial_fields()
        res += ['siren', 'nic']
        return res

    siren = fields.Char(
        string='SIREN', size=9, track_visibility='onchange',
        help="The SIREN number is the official identity "
        "number of the company in France. It makes "
        "the first 9 digits of the SIRET number.")
    nic = fields.Char(
        string='NIC', size=5, track_visibility='onchange',
        help="The NIC number is the official rank number "
        "of this office in the company in France. It "
        "makes the last 5 digits of the SIRET "
        "number.")
    siret = fields.Char(
        compute='_get_siret', string='SIRET', size=14, store=True,
        help="The SIRET number is the official identity number of this "
        "company's office in France. It is composed of the 9 digits "
        "of the SIREN number and the 5 digits of the NIC number, ie. "
        "14 digits.")
    company_registry = fields.Char(
        string='Company Registry', size=64,
        help="The name of official registry where this company was declared.")
