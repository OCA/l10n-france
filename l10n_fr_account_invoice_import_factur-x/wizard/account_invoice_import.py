# -*- coding: utf-8 -*-
# Copyright 2018 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountInvoiceImport(models.TransientModel):
    _inherit = 'account.invoice.import'

    def prepare_facturx_xpath_dict(self):
        xpathd = super(AccountInvoiceImport, self).prepare_facturx_xpath_dict()
        xpathd['partner']['siret'] = [
            "//ram:ApplicableHeaderTradeAgreement"
            "/ram:SellerTradeParty"
            "/ram:SpecifiedLegalOrganization"
            "/ram:ID[@schemeID='0002']"]
        xpathd['company']['siret'] = [
            "//ram:ApplicableHeaderTradeAgreement"
            "/ram:BuyerTradeParty"
            "/ram:SpecifiedLegalOrganization"
            "/ram:ID[@schemeID='0002']"]
        return xpathd
