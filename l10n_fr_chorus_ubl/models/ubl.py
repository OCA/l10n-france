# -*- coding: utf-8 -*-
# © 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, api

ODOO2CHORUS_TAX_CATEG_CODE = {
    'debit': 'TVA DEBIT',
    'cashin': 'TVA ENCAISSEMENT',
    }


class BaseUbl(models.Model):
    # inherit base.ubl in v10
    _inherit = 'account.invoice'

    @api.model
    def _ubl_get_tax_scheme_dict_from_tax(self, tax):
        res = super(BaseUbl, self)._ubl_get_tax_scheme_dict_from_tax(tax)
        if (
                self._context.get('fr_chorus') and
                tax.unece_type_code == 'VAT'):
            res['type_code'] = 'TVA'
        return res

    @api.model
    def _ubl_get_tax_scheme_dict_from_partner(self, commercial_partner):
        res = super(BaseUbl, self)._ubl_get_tax_scheme_dict_from_partner(
            commercial_partner)
        if commercial_partner.fr_vat_scheme:
            code = ODOO2CHORUS_TAX_CATEG_CODE[commercial_partner.fr_vat_scheme]
            res['type_code'] = code
        return res

    @api.model
    def _ubl_get_party_identification(self, commercial_partner):
        res = super(BaseUbl, self)._ubl_get_party_identification(
            commercial_partner)
        # partner.siret has a value even if partner.nic == False
        if (
                self._context.get('fr_chorus') and
                commercial_partner.siren and
                commercial_partner.nic):
            res['1'] = commercial_partner.siret
        return res

    @api.model
    def _ubl_get_contact_id(self, partner):
        if self._context.get('fr_chorus') and partner.fr_chorus_service_code:
            return partner.fr_chorus_service_code
        return super(BaseUbl, self)._ubl_get_contact_id(partner)
