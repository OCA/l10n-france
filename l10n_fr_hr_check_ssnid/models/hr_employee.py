# Copyright 2018-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, models
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)

try:
    from stdnum.fr.nir import InvalidChecksum, InvalidFormat, InvalidLength, validate
except ImportError:
    logger.debug("Cannot import stdnum")


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.constrains("ssnid")
    def france_ssnid_constrain(self):
        for empl in self:
            if empl.company_id.country_id.code == "FR" and empl.ssnid:
                try:
                    validate(empl.ssnid)
                except (InvalidFormat, InvalidLength, InvalidChecksum) as e:
                    raise ValidationError(
                        _("The French Social Security Number '%s' is invalid. " "(%s)")
                        % (empl.ssnid, e)
                    )
