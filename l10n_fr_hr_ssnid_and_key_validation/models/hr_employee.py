# -*- coding: utf-8 -*-
# Copyright 2020 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models
from odoo.exceptions import ValidationError
import logging
logger = logging.getLogger(__name__)

try:
    from stdnum import get_cc_module
    from stdnum.exceptions import (
        InvalidChecksum,
        InvalidComponent,
        InvalidFormat,
        InvalidLength,
    )
except ImportError:
    logger.debug('Cannot import stdnum')

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    ssnid_key = fields.Char(
        string='SSN No Key',
        help='Social Security Number Key',
        size=2,
        required=True,
    )

    @api.onchange('ssnid', 'ssnid_key')
    def onchange_ssnid(self):
        self.check_ssnid()

    @api.constrains('ssnid', 'ssnid_key')
    def check_ssnid(self):
        # We assume this dev work only in France
        # other available format are on
        # https://arthurdejong.org/python-stdnum/doc/1.13/index.html#available-formats
        for rec in self:
            if rec.company_id.country_id.code == 'FR' and rec.ssnid:
                mod = get_cc_module('fr', 'nir')
                ssnid_global = rec.ssnid + rec.ssnid_key
                try:
                    mod.validate(ssnid_global)
                except InvalidFormat as expt:
                    msg = "The ssnid format is invalid :\n{}".format(expt)
                    raise ValidationError(msg)
                except InvalidChecksum as expt:
                    msg = "The ssnid checksum is invalid  :\n{}".format(expt)
                    raise ValidationError(msg)
                except InvalidLength as expt:
                    msg = "The ssnid length is invalid :\n{}".format(expt)
                    raise ValidationError(msg)
                except InvalidComponent as expt:
                    msg = "One of the parts of ssnid has an invalid reference :\n{}".format(
                        expt
                    )
                    raise ValidationError(msg)
                except Exception as expt:
                    msg = "Issue in ssnid check :\n{}".format(expt)
                    raise ValidationError(msg)
