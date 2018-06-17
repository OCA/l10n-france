# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from hashlib import sha256
from json import dumps

from openerp import _, api, fields, models
from openerp.exceptions import Warning as UserError


class CertificationModelMixin(models.AbstractModel):
    _name = 'certification.model.mixin'

    _SELECTION_CERTIFICATION_STATE = [
        ('not_concerned', 'Not Concerned'),
        ('certified', 'Certified'),
        ('corrupted', 'Corrupted'),
    ]

    l10n_fr_secure_sequence_number = fields.Integer(
        readonly=True, copy=False, string='Security Sequence Number')

    l10n_fr_hash = fields.Char(
        readonly=True, copy=False, string='Security Hash')

    l10n_fr_string_to_hash = fields.Char(
        compute='_compute_l10n_fr_string_to_hash', string='hashed Data')

    l10n_fr_is_locked = fields.Boolean(
        compute='_compute_l10n_fr_is_locked', string='Locked')

    l10n_fr_secure_state = fields.Selection(
        string='Inalterability State',
        compute='_compute_l10n_fr_secure_state',
        selection=_SELECTION_CERTIFICATION_STATE, help="State of the hash.\n"
        " * 'Not Concerned' : The hash has not be generated. No Inalteribiliy"
        " can be granted\n"
        " * 'Certified': The stored hash is conform with the current data"
        " Inalteribiliy is granted\n"
        " * 'Corrupted': The stored hash is not conform with the current data")

    # Section - Abstract constants to be overwritten
    """Should provides field name of the related One2Many Field which
    data should be hashed. Exemple : 'line_ids'"""
    _secured_line_field_name = False

    """Should provides the name of the field that host the sequence for
    the current model. Exemple: 'company_id'"""
    _sequence_holder_field_name = False

    """ Should provides the list of the states that blocks changes of items.
    Exemple ['posted', 'confirmed']"""
    _locked_state_list = []

    """fields names list to be integrated in the hash computation.
    Exemple : ['partner_id', 'total']"""
    _secured_field_name_list = []

    @api.multi
    def _get_sequence_holder(self):
        """Should return the object that hold the sequence that manages
        security"""
        self.ensure_one()
        raise UserError(_("Unimplemented Feature"))

    # Custom Section
    @api.multi
    def security_required(self):
        """Return True if security process should be applied
        depending of company settings"""
        self.ensure_one()
        return self._get_sequence_holder().security_required()

    @api.multi
    def check_write_allowed(self, vals):
        """Raise an error if updating the items if forbidden with the
        given values"""
        locked_items = [x for x in self if x.l10n_fr_is_locked]
        if not locked_items:
            return
        if 'state' in vals.keys():
            raise UserError(_(
                "According to the french law, you cannot modify the state"
                " of the following items\n%s") % (
                    ','.join([x.name for x in locked_items])))
        intersec = set(vals).intersection(self._secured_field_name_list)
        if intersec:
            raise UserError(_(
                "According to the french law, you cannot change the value"
                " of the field %s for the following items\n%s") % (
                    ','.join(intersec),
                    ','.join([x.name for x in locked_items])))

    @api.multi
    def _compute_current_hash(self, last_number):
        """Return the hash of an object, computed on its current data_
        (l10n_fr_string_to_hash) and the hash of the previous object (if
        exist)"""
        self.ensure_one()
        obj = self
        if last_number == 0:
            previous_hash = ''
        else:
            previous_obj = self.search([
                (
                    obj._sequence_holder_field_name, '=',
                    obj._get_sequence_holder().id),
                ('l10n_fr_secure_sequence_number', '=', last_number)])
            if len(previous_obj) != 1:
                raise UserError(_(
                    "Error occured when computing the hash. Impossible"
                    " to get the unique previous validated item."))
            previous_hash = previous_obj.l10n_fr_hash
        return sha256(
            previous_hash + obj.l10n_fr_string_to_hash).hexdigest()

    @api.multi
    def generate_hash(self):
        sequence_obj = self.env['ir.sequence']
        for obj in self:
            if obj.security_required():
                if obj.l10n_fr_secure_sequence_number != 0:
                    raise UserError(_(
                        "you can not regenerate hash for this item because"
                        " it has yet a sequence number defined"))
                new_number = sequence_obj.next_by_id(
                    obj._get_sequence_holder().l10n_fr_secure_sequence_id.id)
                last_number = int(new_number) - 1
                new_hash = obj._compute_current_hash(last_number)
                vals_hashing = {
                    'l10n_fr_secure_sequence_number': new_number,
                    'l10n_fr_hash': new_hash,
                }
                super(CertificationModelMixin, obj).write(vals_hashing)

    # Compute Section
    @api.multi
    def _compute_l10n_fr_secure_state(self):
        for obj in self:
            if obj.l10n_fr_secure_sequence_number == 0\
                    and not obj.l10n_fr_hash:
                obj.l10n_fr_secure_state = 'not_concerned'
            elif obj.l10n_fr_hash != obj._compute_current_hash(
                    obj.l10n_fr_secure_sequence_number - 1):
                obj.l10n_fr_secure_state = 'corrupted'
            else:
                obj.l10n_fr_secure_state = 'certified'

    @api.multi
    def _compute_l10n_fr_is_locked(self):
        for obj in self:
            obj.l10n_fr_is_locked =\
                obj._get_sequence_holder().security_required() and\
                obj.l10n_fr_secure_sequence_number != 0

    def _compute_l10n_fr_string_to_hash(self):
        def _getattrstring(obj, field_str):
            field_value = obj[field_str]
            if obj._fields[field_str].type == 'many2one':
                field_value = field_value.id
            return str(field_value)

        for obj in self:
            values = {}
            for field in self._secured_field_name_list:
                values[field] = _getattrstring(obj, field)

            # This algorithm seems pretty bad
            # https://github.com/odoo/odoo/issues/17671
            # https://github.com/odoo/odoo/pull/16935/files#r122426669
            # TODO WAIT ODOO SA Fix and FIXME
            # if self._hash_line_field_name:
            #    for line in getattr(obj, self._todo):
            #        for field in line._todo:
            #            values[field] = _getattrstring(line, field)
            obj.l10n_fr_string_to_hash = dumps(
                values, sort_keys=True, encoding="utf-8", ensure_ascii=True,
                indent=None, separators=(',', ':'))
