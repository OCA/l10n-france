# Copyright 2017-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.account_payment_unece.tests.test_account_invoice import \
    TestAccountInvoice


class TestUblInvoice(TestAccountInvoice):

    def test_chorus_ubl(self):
        invoice = self.test_only_create_invoice()
        agreement = self.env.ref('l10n_fr_chorus_account.market3')
        partner = self.env.ref(
            'l10n_fr_chorus_account.national_education_ministry_service1')
        invoice.write({
            'agreement_id': agreement.id,
            'partner_id': partner.id,
            'name': 'EJ1242',
            })
        action = invoice.attach_ubl_xml_file_button()
        self.assertEqual(action['res_model'], 'ir.attachment')
        attach = self.env['ir.attachment'].browse(action['res_id'])
        self.assertEqual(attach.datas_fname[-4:], '.xml')
