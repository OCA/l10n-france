# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from datetime import date

from odoo.addons.account.tests.account_test_classes import AccountingTestCase


# Most setup is copied from odoo accounting bank_statement_reconcilation tests
class TestPostOnValidation(AccountingTestCase):
    def setUp(self):
        super(TestPostOnValidation, self).setUp()
        self.i_model = self.env['account.invoice']
        self.il_model = self.env['account.invoice.line']
        self.bs_model = self.env['account.bank.statement']
        self.bsl_model = self.env['account.bank.statement.line']
        self.partner = self.env['res.partner'].create({'name': 'test'})

    def test_full_reconcile(self):
        self._reconcile_invoice_with_statement(False)

    def test_post_at_bank_rec_full_reconcile(self):
        self._reconcile_invoice_with_statement(True)

    def _reconcile_invoice_with_statement(self, post_at_bank_rec):
        # The post_at_bank_reconciliation flag changes when the move is posted.
        # we want to make sure our addon is working with both settings,
        # so this function is used twice
        self.bs_model.with_context(
            journal_type='bank'
        )._default_journal().post_at_bank_reconciliation = post_at_bank_rec
        rcv_mv_line = self.create_invoice(100)
        st_line = self.create_statement_line(100)
        # reconcile
        st_line.process_reconciliation(
            counterpart_aml_dicts=[
                {
                    'move_line': rcv_mv_line,
                    'credit': 100,
                    'debit': 0,
                    'name': rcv_mv_line.name,
                }
            ]
        )

        # check everything went as expected
        self.assertTrue(st_line.journal_entry_ids)
        move = st_line.journal_entry_ids.mapped('move_id')
        self.assertEqual(move.state, 'draft')
        st_line.statement_id.balance_end_real = 100.0
        st_line.statement_id.button_confirm_bank()
        self.assertEqual(move.state, 'posted')

    def create_invoice(self, amount):
        vals = {
            'partner_id': self.partner.id,
            'type': 'out_invoice',
            'name': '-',
            'currency_id': self.env.user.company_id.currency_id.id,
        }
        # new creates a temporary record to apply the on_change afterwards
        invoice = self.i_model.new(vals)
        invoice._onchange_partner_id()
        vals.update({'account_id': invoice.account_id.id})
        self.invoice = self.i_model.create(vals)

        self.il_model.create(
            {
                'quantity': 1,
                'price_unit': amount,
                'invoice_id': self.invoice.id,
                'name': '.',
                'account_id': self.env['account.account']
                .search(
                    [
                        (
                            'user_type_id',
                            '=',
                            self.env.ref(
                                'account.data_account_type_revenue'
                            ).id,
                        )
                    ],
                    limit=1,
                )
                .id,
            }
        )
        self.invoice.action_invoice_open()

        mv_line = None
        for line in self.invoice.move_id.line_ids:
            if line.account_id.id == vals['account_id']:
                mv_line = line
        self.assertIsNotNone(mv_line)

        return mv_line

    def create_statement_line(self, st_line_amount):
        journal = self.bs_model.with_context(
            journal_type='bank'
        )._default_journal()
        bank_stmt = self.bs_model.create({'journal_id': journal.id})

        bank_stmt_line = self.bsl_model.create(
            {
                'name': '_',
                'statement_id': bank_stmt.id,
                'partner_id': self.partner.id,
                'amount': st_line_amount,
            }
        )

        return bank_stmt_line

    def test_reconcile_with_account_payment(self):
        journal = self.bs_model.with_context(
            journal_type='bank'
        )._default_journal()
        journal.post_at_bank_reconciliation = True
        rcv_mv_line = self.create_invoice(100)
        payment = self.env['account.payment'].create(
            {
                'payment_type': 'inbound',
                'payment_method_id': self.env.ref(
                    'account.account_payment_method_manual_in'
                ).id,
                'partner_type': 'customer',
                'partner_id': self.partner.id,
                'amount': 100,
                'currency_id': self.currency_usd_id,
                'payment_date': date.today(),
                'journal_id': journal.id,
            }
        )
        payment.post()
        payment_move_line = False
        for line in payment.move_line_ids:
            if line.account_id.user_type_id.name == 'Receivable':
                payment_move_line = line
        self.invoice.register_payment(payment_move_line)

        st_line = self.create_statement_line(100)
        # reconcile
        st_line.process_reconciliation(
            counterpart_aml_dicts=[
                {
                    'move_line': rcv_mv_line,
                    'credit': 100,
                    'debit': 0,
                    'name': rcv_mv_line.name,
                }
            ]
        )

        # check everything went as expected
        self.assertTrue(st_line.journal_entry_ids)
        move = st_line.journal_entry_ids.mapped('move_id')
        self.assertEqual(move.state, 'draft')
        st_line.statement_id.balance_end_real = 100.0
        st_line.statement_id.button_confirm_bank()
        self.assertEqual(move.state, 'posted')
