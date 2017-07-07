# -*- coding: utf-8 -*-
# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# Copyright (C) 2017 - Today: Akretion (http://www.akretion.com)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import _, api, fields, models
from openerp.exceptions import Warning as UserError


class CertificationSequenceHolderMixin(models.AbstractModel):
    _name = 'certification.sequence.holder.mixin'

    # Section - Field
    l10n_fr_secure_sequence_id = fields.Many2one(
        comodel_name='ir.sequence', readonly=True, copy=False,
        string='Security Sequence',
        help="Sequence to use to ensure the securisation of data")

    # Section - Abstract constants to be overwritten
    """Secured Model by this holder"""
    _secured_model_name = False

    # Section - Abstract function to be overwritten
    @api.multi
    def _get_certification_country(self):
        """Should return the country of the current holder"""
        self.ensure_one()
        raise UserError(_("Unimplemented Feature"))

    @api.multi
    def _get_certification_company(self):
        """Should return the company of the current holder"""
        self.ensure_one()
        raise UserError(_("Unimplemented Feature"))

    # Overload Section
    @api.model
    def create(self, vals):
        obj = super(CertificationSequenceHolderMixin, self).create(vals)
        obj.generate_secure_sequence_if_required()
        return obj

    # Custom Section
    @api.multi
    def security_required(self):
        self.ensure_one()
        return self._get_certification_country() == self.env.ref('base.fr')

    @api.multi
    def generate_secure_sequence_if_required(self):
        for obj in self:
            if not obj.l10n_fr_secure_sequence_id and obj.security_required():
                obj._create_secure_sequence()

    @api.multi
    def _create_secure_sequence(self):
        """This function creates a no_gap sequence on each holder in self
        that will ensure a unique number is given to all items of
        the secured model, in such a way that we can always find the previous
        item for all items.
        """
        for obj in self:
            vals = {
                'name': 'French Securisation of %s - %s' % (
                    self._secured_model_name, obj.name),
                'implementation': 'no_gap',
                'prefix': '',
                'suffix': '',
                'padding': 0,
                'company_id': self._get_certification_company().id}
            seq = self.env['ir.sequence'].create(vals)
            obj.write({'l10n_fr_secure_sequence_id': seq.id})
