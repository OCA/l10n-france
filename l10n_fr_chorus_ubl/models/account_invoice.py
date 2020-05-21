# Copyright 2017-2020 Akretion France (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def generate_ubl_xml_string(self, version='2.1'):
        self.ensure_one()
        if self.transmit_method_code == 'fr-chorus':
            self = self.with_context(fr_chorus=True)
        return super(AccountInvoice, self).generate_ubl_xml_string(
            version=version)

    def _ubl_get_contract_document_reference_dict(self):
        self.ensure_one()
        cdr_dict = super(AccountInvoice, self).\
            _ubl_get_contract_document_reference_dict()
        if self.agreement_id:
            cdr_dict['Marché public'] = self.agreement_id.code
        return cdr_dict

    def chorus_get_invoice(self, chorus_invoice_format):
        self.ensure_one()
        if chorus_invoice_format == 'xml_ubl':
            chorus_file_content = self.generate_ubl_xml_string()
        else:
            chorus_file_content = super(AccountInvoice, self).\
                chorus_get_invoice(chorus_invoice_format)
        return chorus_file_content
