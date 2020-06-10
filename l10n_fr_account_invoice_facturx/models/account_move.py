# Copyright 2017-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _cii_get_party_identification(self, commercial_partner):
        res = super()._cii_get_party_identification(commercial_partner)
        # partner.siret has a value even if partner.nic == False
        if commercial_partner.siren and commercial_partner.nic:
            res['0002'] = commercial_partner.siret
        return res
