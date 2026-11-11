# Copyright 2018-2020 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)

try:
    from stdnum.fr.nir import InvalidChecksum, InvalidFormat, InvalidLength, validate
except ImportError:
    logger.debug("Cannot import stdnum")


class HrVersion(models.Model):
    _inherit = "hr.version"

    @api.constrains("identification_id", "company_id")
    def _check_france_ssnid(self):
        for empl in self:
            if empl.company_id.is_france_country and empl.identification_id:
                try:
                    validate(empl.identification_id)
                except (InvalidFormat, InvalidLength, InvalidChecksum) as e:
                    raise ValidationError(
                        self.env._(
                            "The French Social Security Number '%(ssnid)s' "
                            "is invalid. %(e)s",
                            ssnid=empl.identification_id,
                            e=e,
                        )
                    ) from e
