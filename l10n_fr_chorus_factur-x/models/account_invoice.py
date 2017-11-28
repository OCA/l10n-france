# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _cii_trade_contact_department_name(self, partner):
        if partner.fr_chorus_service_code:
            return partner.name
        return super(AccountInvoice, self)._cii_trade_contact_department_name(
            partner)

    @api.model
    def _cii_trade_agreement_buyer_ref(self, partner):
        if partner.fr_chorus_service_code:
            return partner.fr_chorus_service_code
        return super(AccountInvoice, self)._cii_trade_contact_department_name(
            partner)
