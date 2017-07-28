# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _cii_get_party_identification(self, commercial_partner):
        res = super(AccountInvoice, self)._cii_get_party_identification(
            commercial_partner)
        # partner.siret has a value even if partner.nic == False
        if commercial_partner.siren and commercial_partner.nic:
            res['0002'] = commercial_partner.siret
        return res
