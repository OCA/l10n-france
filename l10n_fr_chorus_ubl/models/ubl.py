# -*- coding: utf-8 -*-
# Copyright 2017-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
import logging

logger = logging.getLogger(__name__)


UNECE2CHORUS_TAX_CATEG_CODE = {
    '5': 'TVA DEBIT',
    '72': 'TVA ENCAISSEMENT',
    }


class BaseUbl(models.AbstractModel):
    _inherit = 'base.ubl'

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
        company = self.env['res.company'].search(
            [('partner_id', '=', commercial_partner.id)], limit=1)
        if company:
            tax_ids = self.env['ir.values'].get_default(
                'product.template', 'taxes_id', for_all_users=True,
                company_id=company.id)
            logger.debug(
                'Using default sale tax %s of company %s for UBL TaxScheme',
                tax_ids, company.name)
            if tax_ids:
                tax = self.env['account.tax'].browse(tax_ids[0])
                logger.debug(
                    'First default sale tax (ID %d) has '
                    'unece_due_date_code=%s',
                    tax_ids[0], tax.unece_due_date_code)
                if tax.unece_due_date_code:
                    code = UNECE2CHORUS_TAX_CATEG_CODE[tax.unece_due_date_code]
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
        if self._context.get('fr_chorus') and partner.fr_chorus_service_id:
            return partner.fr_chorus_service_id.code
        return super(BaseUbl, self)._ubl_get_contact_id(partner)
