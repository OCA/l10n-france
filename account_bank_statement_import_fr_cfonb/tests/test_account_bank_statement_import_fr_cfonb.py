# -*- coding: utf-8 -*-

import base64

from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError


class TestImport(TransactionCase):

    def test_import_multi_cfonb(self):
        """ Test importation of cfonb file with multi bank """

        Journal = self.env['account.journal']
        BankAccount = self.env['res.partner.bank']
        BankStatement = self.env['account.bank.statement']
        Currency = self.env['res.currency']
        eur_currency = Currency.search([('name', '=ilike', 'EUR')], limit=1)

        bank_1 = BankAccount.create({
            'acc_number': 'FR7630001007941234567890185'})
        journal_1 = Journal.create({'name': 'BANK 1',
                                    'code': 'ban1',
                                    'type': 'bank',
                                    'bank_account_id': bank_1.id,
                                    'currency_id': eur_currency.id})

        bank_2 = BankAccount.create({
            'acc_number': 'FR7630004000031234567890143'})
        journal_2 = Journal.create({'name': 'BANK 2',
                                    'code': 'ban2',
                                    'type': 'bank',
                                    'bank_account_id': bank_2.id,
                                    'currency_id': eur_currency.id})

        Wizard = self.env['account.bank.statement.import']

        cfonb_file_path = get_module_resource(
            'account_bank_statement_import_fr_cfonb',
            'tests',
            'test_cfonb.txt')

        cfonb_file = base64.b64encode(open(cfonb_file_path, 'rb').read())

        wizard = Wizard.create({'data_file': cfonb_file})
        wizard.import_file()

        statement_1 = BankStatement.search([('journal_id', '=', journal_1.id)])
        self.assertEqual(len(statement_1), 1)
        self.assertEqual(len(statement_1.line_ids), 4)
        statement_2 = BankStatement.search([('journal_id', '=', journal_2.id)])
        self.assertEqual(len(statement_2), 1)
        self.assertEqual(len(statement_2.line_ids), 3)

        cfonb_file = base64.b64encode(open(cfonb_file_path, 'rb').read())
        wizard = Wizard.create({'data_file': cfonb_file})
        with self.assertRaises(UserError):
            wizard.import_file()

        # TEST One line file
        statement_1.unlink()
        statement_2.unlink()

        cfonb_file_path = get_module_resource(
            'account_bank_statement_import_fr_cfonb',
            'tests',
            'test_cfonb_one_line.txt')

        cfonb_file = base64.b64encode(open(cfonb_file_path, 'rb').read())

        wizard = Wizard.create({'data_file': cfonb_file})
        wizard.import_file()

        statement_1 = BankStatement.search([('journal_id', '=', journal_1.id)])
        self.assertEqual(len(statement_1), 1)
        self.assertEqual(len(statement_1.line_ids), 4)
        statement_2 = BankStatement.search([('journal_id', '=', journal_2.id)])
        self.assertEqual(len(statement_2), 1)
        self.assertEqual(len(statement_2.line_ids), 3)

    def test_empty_line(self):
        """ Test importation of empty file """
        Wizard = self.env['account.bank.statement.import']
        cfonb_file_path = get_module_resource(
            'account_bank_statement_import_fr_cfonb',
            'tests',
            'test_cfonb_empty_line.txt')

        cfonb_file = base64.b64encode(open(cfonb_file_path, 'rb').read())
        wizard = Wizard.create({'data_file': cfonb_file})
        with self.assertRaises(UserError):
            wizard.import_file()

    def test_other_file(self):
        """ Test importation of other_file """
        Wizard = self.env['account.bank.statement.import']
        cfonb_file_path = get_module_resource(
            'account_bank_statement_import_fr_cfonb',
            'tests',
            'test_cfonb_other_file.txt')

        cfonb_file = base64.b64encode(open(cfonb_file_path, 'rb').read())
        wizard = Wizard.create({'data_file': cfonb_file})
        with self.assertRaises(UserError):
            wizard.import_file()

    def test_cfonb_file_with_bad_lenght(self):
        """ Test importation of bad lenght """
        Wizard = self.env['account.bank.statement.import']
        cfonb_file_path = get_module_resource(
            'account_bank_statement_import_fr_cfonb',
            'tests',
            'test_cfonb_bad_lenght.txt')

        cfonb_file = base64.b64encode(open(cfonb_file_path, 'rb').read())
        wizard = Wizard.create({'data_file': cfonb_file})
        with self.assertRaises(UserError):
            wizard.import_file()

    def test_cfonb_file_with_bad_decimal(self):
        """ Test importation of bad decimal """
        Wizard = self.env['account.bank.statement.import']
        cfonb_file_path = get_module_resource(
            'account_bank_statement_import_fr_cfonb',
            'tests',
            'test_cfonb_bad_decimal.txt')

        cfonb_file = base64.b64encode(open(cfonb_file_path, 'rb').read())
        wizard = Wizard.create({'data_file': cfonb_file})
        with self.assertRaises(UserError):
            wizard.import_file()

    def test_cfonb_file_with_iban_diff_04(self):
        """ Test importation of iban diff 04 """
        Wizard = self.env['account.bank.statement.import']
        cfonb_file_path = get_module_resource(
            'account_bank_statement_import_fr_cfonb',
            'tests',
            'test_cfonb_iban_diff_04.txt')

        cfonb_file = base64.b64encode(open(cfonb_file_path, 'rb').read())
        wizard = Wizard.create({'data_file': cfonb_file})
        with self.assertRaises(UserError):
            wizard.import_file()

    def test_cfonb_file_with_iban_diff_07(self):
        """ Test importation of iban diff 07 """
        Wizard = self.env['account.bank.statement.import']
        cfonb_file_path = get_module_resource(
            'account_bank_statement_import_fr_cfonb',
            'tests',
            'test_cfonb_iban_diff_07.txt')

        cfonb_file = base64.b64encode(open(cfonb_file_path, 'rb').read())
        wizard = Wizard.create({'data_file': cfonb_file})
        with self.assertRaises(UserError):
            wizard.import_file()

    def test_cfonb_inv_04_05(self):
        """ Test importation of inversion 04 05 """
        Wizard = self.env['account.bank.statement.import']
        cfonb_file_path = get_module_resource(
            'account_bank_statement_import_fr_cfonb',
            'tests',
            'test_cfonb_inv_04_05.txt')

        cfonb_file = base64.b64encode(open(cfonb_file_path, 'rb').read())
        wizard = Wizard.create({'data_file': cfonb_file})
        with self.assertRaises(UserError):
            wizard.import_file()

    def test_rib_with_letter(self):
        """ test rib with letter """
        Wizard = self.env['account.bank.statement.import']
        result = Wizard._RIBwithoutkey2IBAN('30001', '00794', '1234567890A')
        self.assertEqual('FR7630001007941234567890185', result)
