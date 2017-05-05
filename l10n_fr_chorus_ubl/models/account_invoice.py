# -*- coding: utf-8 -*-
# © 2017 Akretion (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def generate_ubl_xml_string(self, version='2.1'):
        self.ensure_one()
        if self.transmit_method_code == 'fr-chorus':
            self = self.with_context(fr_chorus=True)
        return super(AccountInvoice, self).generate_ubl_xml_string(
            version=version)

    @api.multi
    def _ubl_get_contract_document_reference_dict(self):
        self.ensure_one()
        cdr_dict = super(AccountInvoice, self).\
            _ubl_get_contract_document_reference_dict()
        if self.public_market_id:
            cdr_dict[u'Marché public'] = self.public_market_id.code
        return cdr_dict
