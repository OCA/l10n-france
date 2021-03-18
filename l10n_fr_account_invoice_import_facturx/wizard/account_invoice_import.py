# Copyright 2018-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountInvoiceImport(models.TransientModel):
    _inherit = 'account.invoice.import'

    def prepare_facturx_xpath_dict(self):
        xpathd = super().prepare_facturx_xpath_dict()
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

    # If one day we have a module l10n_fr_account_invoice_import
    # we could move the inherit of _prepare_new_partner_context() there
    def _prepare_new_partner_context(self, parsed_inv):
        context = super()._prepare_new_partner_context(parsed_inv)
        if parsed_inv['partner'].get('siren'):
            context['default_siren'] = parsed_inv['partner']['siren']
        elif parsed_inv['partner'].get('siret'):
            context['default_siren'] = parsed_inv['partner']['siret'][:9]
            context['default_nic'] = parsed_inv['partner']['siret'][9:14]
        return context
