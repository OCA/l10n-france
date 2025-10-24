from odoo import Command
from odoo.exceptions import AccessDenied, UserError
from odoo.tests.common import tagged

from odoo.addons.l10n_fr_account.tests.test_fec_export import TestFECExport


@tagged("post_install_l10n", "post_install", "-at_install")
class TestFECExportOCA(TestFECExport):
    def test_fec_export_with_user(self):
        user_demo = self.env.ref("base.user_demo")
        self.init_invoice(
            "out_invoice", self.partner_a, "2019-01-01", amounts=[1000, 2000], post=True
        )
        inv = self.init_invoice(
            "out_invoice", self.partner_a, "2020-01-01", amounts=[1000, 2000]
        )
        inv.write(
            {
                "line_ids": [
                    Command.create(
                        {
                            "name": "Note",
                            "display_type": "line_note",
                        }
                    )
                ]
            }
        )
        inv.action_post()
        # Create a new FEC export
        fec_export_wz = self.env["l10n_fr.fec.export.wizard"]
        with self.assertRaises(AccessDenied):
            vals = {
                "date_from": "2020-01-01",
                "date_to": "2020-12-31",
            }
            fec_export = fec_export_wz.create(vals)
            fec_export.with_user(user_demo).create_fec_report_action()
        with self.assertRaises(UserError):
            vals = {
                "date_from": "2020-12-31",
                "date_to": "2020-01-01",
            }
            fec_export = fec_export_wz.create(vals)
            fec_export.with_user(user_demo).create_fec_report_action()

    def test_fec_export_with_partner_ref(self):
        self.partner_a.write(
            {
                "ref": "REF0001",
            }
        )
        self.init_invoice(
            "out_invoice", self.partner_a, "2019-01-01", amounts=[1000, 2000], post=True
        )
        inv = self.init_invoice(
            "out_invoice", self.partner_a, "2020-01-01", amounts=[1000, 2000]
        )
        inv.write(
            {
                "line_ids": [
                    Command.create(
                        {
                            "name": "Note",
                            "display_type": "line_note",
                        }
                    )
                ]
            }
        )
        inv.action_post()
        # Create a new FEC export
        fec_export = self.env["l10n_fr.fec.export.wizard"].create(
            {
                "date_from": "2020-01-01",
                "date_to": "2020-12-31",
                "partner_identifier": "ref",
            }
        )
        result = fec_export.generate_fec()
        self.assertEqual(
            result["file_content"].decode(),
            "JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise\r\n"  # noqa: E501
            "OUV|Balance initiale|OUVERTURE/2020|20200101|999999|Undistributed Profits/Losses|||-|20200101|/|0,00| 000000000003000,00|||20200101||\r\n"  # noqa: E501
            f"OUV|Balance initiale|OUVERTURE/2020|20200101|121000|Account Receivable|{self.partner_a.ref}|partner_a|-|20200101|/| 000000000003000,00|0,00|||20200101||\r\n"  # noqa: E501
            "INV|Customer Invoices|INV/2020/00001|20200101|400000|Product Sales|||-|20200101|test line|0,00| 000000000001000,00|||20200101|-000000000001000,00|USD\r\n"  # noqa: E501
            "INV|Customer Invoices|INV/2020/00001|20200101|400000|Product Sales|||-|20200101|test line|0,00| 000000000002000,00|||20200101|-000000000002000,00|USD\r\n"  # noqa: E501
            f"INV|Customer Invoices|INV/2020/00001|20200101|121000|Account Receivable|{self.partner_a.ref}|partner_a|-|20200101|INV/2020/00001| 000000000003000,00|0,00|||20200101| 000000000003000,00|USD",  # noqa: E501
        )
