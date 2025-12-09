# Copyright 2024 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestFrLcr(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.order_obj = cls.env["account.payment.order"]
        cls.eur_currency = cls.env.ref("base.EUR")
        cls.today = fields.Date.today()
        cls.today_plus2 = cls.today + timedelta(days=2)
        cls.test_company_dict = cls.setup_other_company(
            name="LCR Company",
            currency_id=cls.eur_currency.id,
        )
        cls.company = cls.test_company_dict["company"]
        cls.env.user.write(
            {
                "group_ids": [
                    Command.link(
                        cls.env.ref(
                            "account_payment_batch_oca.group_account_payment"
                        ).id
                    )
                ],
                "company_ids": [Command.link(cls.company.id)],
            }
        )
        cls.in_payment_account = cls.env["account.account"].create(
            {
                "code": "511500XX",
                "name": "Test Incoming Payment Account",
                "account_type": "asset_current",
                "reconcile": True,
                "company_ids": [Command.link(cls.company.id)],
            }
        )

        cls.partner1 = cls.env["res.partner"].create(
            {
                "name": "Customer1 LCR",
                "company_id": cls.company.id,
            }
        )
        cls.partner1_bank1 = cls.env["res.partner.bank"].create(
            {
                "acc_number": "73925873265832",  # Not an IBAN
                "partner_id": cls.partner1.id,
            }
        )
        cls.partner1_bank2 = cls.env["res.partner.bank"].create(
            {
                "acc_number": "DK11 1234 5678 4444 99",
                "partner_id": cls.partner1.id,
            }
        )

        cls.partner1_bank3 = cls.env["res.partner.bank"].create(
            {
                "acc_number": "FR89 1111 9999 8888 5555 9999 987",
                "partner_id": cls.partner1.id,
            }
        )
        cls.partner1_bank4 = cls.env["res.partner.bank"].create(
            {
                "acc_number": "FR31 5353 4646 1212 7474 2323 678",
                "partner_id": cls.partner1.id,
            }
        )

        cls.partner2 = cls.env["res.partner"].create(
            {
                "name": "Customer2 LCR",
                "company_id": cls.company.id,
            }
        )
        cls.partner2_bank1 = cls.env["res.partner.bank"].create(
            {
                "acc_number": "FR04 1212 2626 3636 4646 4747 676",
                "partner_id": cls.partner2.id,
            }
        )
        cls.partner2_bank2 = cls.env["res.partner.bank"].create(
            {
                "acc_number": "FR89 5454 7777 3434 6363 7654 987",
                "partner_id": cls.partner2.id,
            }
        )
        cls.bank = cls.env["res.bank"].create(
            {
                "name": "Banque Populaire Méditerranée",
                "bic": "CCBPFRPPMAR",
            }
        )
        cls.company_bank = cls.env["res.partner.bank"].create(
            {
                "company_id": cls.company.id,
                "partner_id": cls.company.partner_id.id,
                "bank_id": cls.bank.id,
                "acc_number": "FR10 1212 2323 3434 4545 4747 676",
            }
        )
        cls.bank_journal = cls.env["account.journal"].create(
            {
                "company_id": cls.company.id,
                "name": "Company Bank journal",
                "type": "bank",
                "code": "BNKLC",
                "payment_sequence": False,
                "bank_account_id": cls.company_bank.id,
                "bank_id": cls.company_bank.bank_id.id,
            }
        )
        cls.payment_method_line = cls.env["account.payment.method.line"].create(
            {
                "name": "LCR client",
                "company_id": cls.company.id,
                "payment_method_id": cls.env.ref("account_payment_fr_lcr.fr_lcr").id,
                "bank_account_link": "fixed",
                "journal_id": cls.bank_journal.id,
                "fr_lcr_type": "not_accepted",
                "payment_account_id": cls.in_payment_account.id,
                "selectable": True,
            }
        )

    def create_invoice(self, partner_id, price_unit, inv_type="out_invoice", post=True):
        line_vals = {
            "name": "Great service",
            "quantity": 1,
            "price_unit": price_unit,
        }
        invoice = self.env["account.move"].create(
            {
                "partner_id": partner_id,
                "reference_type": "free",
                "currency_id": self.eur_currency.id,
                "company_id": self.company.id,
                "move_type": inv_type,
                "date": self.today,
                "preferred_payment_method_line_id": self.payment_method_line.id,
                "invoice_line_ids": [Command.create(line_vals)],
            }
        )
        if post:
            invoice.action_post()
            self.assertEqual(invoice.state, "posted")
        else:
            self.assertEqual(invoice.state, "draft")
        return invoice

    def test_prepare_lcr_field(self):
        allowed_chars = "ABCZ0123456789*().,/+-: "
        self.assertEqual(
            self.order_obj._prepare_lcr_field(
                "TEST", allowed_chars, len(allowed_chars)
            ),
            allowed_chars,
        )
        testmap = {
            '42:üûéèàÉÈ?@"^': "42:UUEEAEE----",
            "({non %*€})": "(-NON -*EUR-)",
            "_Niña$;,[]": "-NINA--,--",
            "ça va /pas!.\\|": "CA VA /PAS-.--",
            "narrow white space:\u2009.": "NARROW WHITE SPACE: .",
        }
        for src, dest in testmap.items():
            self.assertEqual(
                self.order_obj._prepare_lcr_field("TEST", src, 30),
                dest + " " * (30 - len(dest)),
            )
        with self.assertRaises(UserError):
            self.order_obj._prepare_lcr_field("TEST", False, 50)
        with self.assertRaises(UserError):
            self.order_obj._prepare_lcr_field("TEST", 42, 50)
        with self.assertRaises(UserError):
            self.order_obj._prepare_lcr_field("TEST", 42.12, 140)
        self.assertEqual(
            self.order_obj._prepare_lcr_field("TEST", "123@ûZZZ", 5), "123-U"
        )
        self.assertEqual(self.order_obj._prepare_lcr_field("TEST", "1234", 2), "12")
        # test reference longer
        self.assertEqual(
            self.order_obj._prepare_lcr_field(
                "TEST", "Fa/2024/0055", 9, reference=True
            ),
            "A20240055",
        )
        # test reference shorter
        self.assertEqual(
            self.order_obj._prepare_lcr_field("TEST", "Fa/24-0055", 10, reference=True),
            "00FA240055",
        )

    def lcr_full_scenario(self):
        invoice1 = self.create_invoice(self.partner1.id, 112.0, post=False)
        self.assertEqual(invoice1.fr_lcr_partner_bank_id, self.partner1_bank3)
        invoice1.fr_lcr_partner_bank_id = self.partner1_bank1.id
        with self.assertRaises(UserError):
            invoice1.action_post()
        invoice1.fr_lcr_partner_bank_id = self.partner1_bank2.id
        with self.assertRaises(UserError):
            invoice1.action_post()
        # change bank account
        invoice1.fr_lcr_partner_bank_id = self.partner1_bank4.id
        invoice1.action_post()
        invoice2 = self.create_invoice(self.partner2.id, 42.0)
        self.assertEqual(invoice2.fr_lcr_partner_bank_id, self.partner2_bank1)
        for inv in [invoice1, invoice2]:
            if inv.payment_method_line_fr_lcr_type == "accepted":
                inv.fr_lcr_print()
                self.assertTrue(inv.fr_lcr_attachment_id)
            action = inv.create_account_payment_line()
        self.assertEqual(action["res_model"], "account.payment.order")
        payment_order = self.order_obj.browse(action["res_id"])
        self.assertEqual(payment_order.payment_type, "inbound")
        self.assertEqual(payment_order.payment_method_line_id, self.payment_method_line)
        self.assertEqual(payment_order.journal_id, self.bank_journal)
        self.assertEqual(
            payment_order.fr_lcr_collection_option,
            payment_order.payment_method_line_id.fr_lcr_default_collection_option,
        )
        self.assertEqual(
            payment_order.fr_lcr_dailly,
            payment_order.payment_method_line_id.fr_lcr_dailly,
        )
        self.assertEqual(
            payment_order.fr_lcr_dailly_option,
            payment_order.payment_method_line_id.fr_lcr_default_dailly_option,
        )
        for line in payment_order.payment_line_ids:
            self.assertEqual(
                line.partner_bank_id, line.move_line_id.move_id.fr_lcr_partner_bank_id
            )
        if payment_order.fr_lcr_collection_option in (
            "cash_discount",
            "value_cash_discount",
        ):
            payment_order.fr_lcr_value_date = self.today_plus2
        payment_order.draft2open()
        self.assertEqual(payment_order.state, "open")
        payment_order.open2generated()
        self.assertEqual(payment_order.state, "generated")
        attachment = payment_order.payment_file_id
        self.assertTrue(attachment)
        self.assertEqual(attachment.name[-4:], ".txt")
        cfonb_bytes = base64.b64decode(attachment.datas)
        cfonb_str = cfonb_bytes.decode("ascii")
        cfonb_lines = cfonb_str.split("\r\n")
        self.assertEqual(len(cfonb_lines), 4)
        return cfonb_lines

    def test_lcr_not_accepted(self):
        self.payment_method_line.write(
            {
                "fr_lcr_type": "not_accepted",
                "fr_lcr_default_collection_option": "due_date",
                "fr_lcr_dailly": False,
            }
        )
        cfonb_lines = self.lcr_full_scenario()
        self.assertEqual(cfonb_lines[0][78], "3")  # code entrée
        self.assertEqual(cfonb_lines[0][79], " ")  # code dailly
        # value date
        self.assertEqual(cfonb_lines[0][118:124], " " * 6)
        for content_line in cfonb_lines[1:-1]:
            # check Acceptation
            self.assertEqual(content_line[78], "0")  # lcr type

    def test_lcr_accepted(self):
        self.payment_method_line.write(
            {
                "fr_lcr_type": "accepted",
                "fr_lcr_default_collection_option": "cash_discount",
                "fr_lcr_dailly": False,
            }
        )

        cfonb_lines = self.lcr_full_scenario()
        self.assertEqual(cfonb_lines[0][78], "1")  # code entrée
        self.assertEqual(cfonb_lines[0][79], " ")  # code dailly
        # value date
        self.assertEqual(cfonb_lines[0][118:124], self.today_plus2.strftime("%d%m%y"))
        for content_line in cfonb_lines[1:-1]:
            self.assertEqual(content_line[78], "1")  # lcr type

    def test_lcr_accepted_dailly(self):
        self.payment_method_line.write(
            {
                "fr_lcr_type": "accepted",
                "fr_lcr_default_collection_option": "due_date",
                "fr_lcr_dailly": True,
                "fr_lcr_default_dailly_option": "cash_discount",
                "fr_lcr_convention_type": "CONV1",
            }
        )
        cfonb_lines = self.lcr_full_scenario()
        self.assertEqual(cfonb_lines[0][78], "3")  # code entrée
        self.assertEqual(cfonb_lines[0][79], "1")  # code dailly
        self.assertEqual(cfonb_lines[0][18:24], "CONV1 ")  # code dailly
        # value date
        self.assertEqual(cfonb_lines[0][118:124], " " * 6)
        for content_line in cfonb_lines[1:-1]:
            self.assertEqual(content_line[78], "1")  # lcr type

    def test_promissory_note(self):
        self.payment_method_line.write(
            {
                "fr_lcr_type": "promissory_note",
                "fr_lcr_default_collection_option": "value_cash_discount",
                "fr_lcr_dailly": False,
            }
        )
        cfonb_lines = self.lcr_full_scenario()
        self.assertEqual(cfonb_lines[0][78], "2")  # code entrée
        self.assertEqual(cfonb_lines[0][79], " ")  # code dailly
        # value date
        self.assertEqual(cfonb_lines[0][118:124], self.today_plus2.strftime("%d%m%y"))
        for content_line in cfonb_lines[1:-1]:
            self.assertEqual(content_line[78], "2")  # lcr type

    def test_iban2rib(self):
        rib = self.partner1_bank3._fr_iban2rib()
        self.assertEqual(rib["bank"], "11119")
        self.assertEqual(rib["branch"], "99988")
        self.assertEqual(rib["account"], "88555599999")
        self.assertEqual(rib["key"], "87")
        self.assertEqual(self.partner1_bank1.acc_type, "bank")
        with self.assertRaises(UserError):
            self.partner1_bank1._fr_iban2rib()
        self.assertEqual(self.partner1_bank2.acc_type, "iban")
        with self.assertRaises(UserError):
            self.partner1_bank2._fr_iban2rib()
