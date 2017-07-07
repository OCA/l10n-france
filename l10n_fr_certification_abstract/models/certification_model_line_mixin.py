# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from hashlib import sha256
from json import dumps

from openerp import _, api, fields, models
from openerp.exceptions import Warning as UserError


class CertificationModelLineMixin(models.AbstractModel):
    _name = 'certification.model.line.mixin'

    # Section Fields
    l10n_fr_is_locked = fields.Boolean(
        compute='_compute_l10n_fr_is_locked', string='Locked')

    # Section - Abstract constants to be overwritten
    """Should provides field name of the related Many2one Field which
    data should be hashed"""
    _secured_model_field_name = False

    """Should provides fields names list to be integrated in the hash
    computation"""
    _secured_field_name_list = []

    # Section - Overload
    @api.multi
    def check_write_allowed(self, vals):
        """Raise an error if updating the items is forbidden with the
        given values"""
        locked_items = [x for x in self if x.l10n_fr_is_locked]
        if not locked_items:
            return
        intersec = set(vals).intersection(self._secured_field_name_list)
        if intersec:
            raise UserError(_(
                "According to the french law, you cannot change the value"
                " of the field %s for the following items\n%s") % (
                    ','.join(intersec),
                    ','.join([x.name for x in locked_items])))

    # Section - Compute
    @api.multi
    def _compute_l10n_fr_is_locked(self):
        for obj in self:
            parent_obj = getattr(obj, self._secured_model_field_name)
            obj.l10n_fr_is_locked = parent_obj.l10n_fr_is_locked
