# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import fields, models, api


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = ['res.company', 'certification.sequence.holder.mixin']

    _secured_model_name = 'account.move'

    @api.multi
    def _get_certification_country(self):
        self.ensure_one()
        return self.country_id

    @api.multi
    def _get_certification_company(self):
        self.ensure_one()
        return self

    @api.multi
    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        # Note: this part of code should be set in the module
        # l10n_fr_certification_abstract, but overloading write function
        # doesn't work for AbstractModel. (even if it works for create
        # function)
        self.generate_secure_sequence_if_required()
        return res
