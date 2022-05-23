# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from datetime import datetime
from dateutil.relativedelta import relativedelta


class TestFrAccountVatReturn(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company']._test_fr_vat_create_company(
            company_name='XXX FR Company VAT')
        self.today = datetime.now().date()
        self.start_date = self.today + relativedelta(months=-1, day=1)
        self.end_date = self.start_date + relativedelta(day=31)
        self.before_date = self.today + relativedelta(months=-3)
        wait_acc = self.get_account('471000')
        credit_acc = self.get_account('445670')
        move = self.env['account.move'].create({
            'company_id': self.company.id,
            'date': self.before_date,
            'journal_id': self.company.fr_vat_journal_id.id,
            'line_ids': [
                (0, 0, {
                    'account_id': credit_acc.id,
                    'debit': 333,
                    }),
                (0, 0, {
                    'account_id': wait_acc.id,
                    'credit': 333,
                    })
                ]})
        move.action_post()

    def get_account(self, code):
        account = self.env['account.account'].search([
            ('code', '=', code),
            ('company_id', '=', self.company.id),
            ], limit=1)
        assert account
        return account

    def test_vat_return(self):
        vat_return = self.env['l10n.fr.account.vat.return'].create({
            'company_id': self.company.id,
            'start_date': self.start_date,
            'vat_periodicity': '1',
            })
        self.assertEqual(vat_return.end_date, self.end_date)
        self.assertEqual(vat_return.state, 'manual')
        self.env['l10n.fr.account.vat.return.line'].create({
            'box_id': self.env.ref('l10n_fr_account_vat_return.a_jb').id,
            'value_manual_int': 134,
            'parent_id': vat_return.id,
            })
        vat_return.manual2auto()
        box2value = {}
        for line in vat_return.line_ids.filtered(lambda x: not x.box_display_type and x.box_edi_type == 'MOA'):
            box2value[(line.box_form_code, line.box_edi_code)] = line.value
        expected_res = {
                'ca3_hd': 333,  # report crédit TVA
                'ca3_hg': 333,  # total VAT deduc
                'a_jb':   134,
                'a_hb':   134,
                'ca3_kb': 134,
                'ca3_ke': 134,
                'ca3_ja': 333,  # credit TVA (ligne 23 - 16)
                'ca3_jc': 333,  # crédit à reporter
                }
        for box_xmlid, expected_value in expected_res.items():
            box = self.env.ref('l10n_fr_account_vat_return.%s' % box_xmlid)
            real_valuebox = box2value.pop((box.form_code, box.edi_code))
            self.assertEqual(real_valuebox, expected_value)
        self.assertFalse(box2value)
        self.assertTrue(vat_return.move_id)
        self.assertEqual(vat_return.move_id.state, 'draft')
        self.assertEqual(vat_return.move_id.date, vat_return.end_date)
        self.assertEqual(vat_return.move_id.journal_id, self.company.fr_vat_journal_id)


