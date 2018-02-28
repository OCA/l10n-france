# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def france_check_ssnid(self, ssnid):
        assert ssnid, 'missing ssnid arg'
        tech_ssnid = ssnid.replace(' ', '').upper()
        if len(tech_ssnid) != 15:
            raise ValidationError(_(
                "French Social Security Numbers should have 15 caracters. "
                "The number '%s' has %d caracters.")
                % (ssnid, len(tech_ssnid)))
        # Handle Corsica
        if tech_ssnid[5:7] == '2A':
            tech_ssnid = '%s19%s' % (tech_ssnid[:5], tech_ssnid[7:])
        elif tech_ssnid[5:7] == '2B':
            tech_ssnid = '%s18%s' % (tech_ssnid[:5], tech_ssnid[7:])
        if not tech_ssnid.isdigit():
            raise ValidationError(_(
                "French Social Security Numbers should only contain digits "
                "(except when the birth department is Corsica). "
                "The number '%s' has non-digit caracters.") % ssnid)
        check_number = int(tech_ssnid[:13])
        checksum = int(tech_ssnid[13:])
        theoric_checksum = 97 - (check_number % 97)
        if checksum != theoric_checksum:
            raise ValidationError(_(
                "The Social Security Number '%s' has an invalid "
                "checksum (%s, should be %s)")
                % (ssnid, checksum, theoric_checksum))
        return True

    @api.constrains('ssnid')
    def france_ssnid_constrain(self):
        for empl in self:
            if empl.company_id.country_id.code == 'FR' and empl.ssnid:
                self.france_check_ssnid(empl.ssnid)
