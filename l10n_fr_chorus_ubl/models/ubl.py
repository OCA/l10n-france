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
            tax = company.account_sale_tax_id
            if tax.unece_due_date_code:
                code = UNECE2CHORUS_TAX_CATEG_CODE[tax.unece_due_date_code]
                res['type_code'] = code
            else:
                logger.warning(
                    'Missing UNECE Due Date on tax %s of company %s',
                    tax.display_name, company.display_name)
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
