import base64

from odoo import Command
from odoo.tests.common import tagged

from odoo.addons.l10n_fr_account.tests.test_fec_export import TestFECExport


@tagged("post_install_l10n", "post_install", "-at_install")
class TestFECExportGroupSalePurchase(TestFECExport):
    def test_fec_export_group_sale_purchase(self):
        fr_company = self.env.company
        fr_company.country_id = self.env.ref("base.fr")
        fr_company.siret = "96851575905808"
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
        fec_export = self.env["account.fr.fec.oca"].create(
            {
                "date_from": "2020-01-01",
                "date_to": "2020-12-31",
                "group_sale_purchase": True,
            }
        )
        fec_export.generate_fec()
        self.assertEqual(
            base64.b64decode(fec_export.fec_data).decode(),
            "JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise\r\n"  # noqa: E501
            "OUV|Balance initiale|OUVERTURE/2020|20200101|999999|Undistributed Profits/Losses|||-|20200101|/|0,00| 000000000003000,00|||20200101||\r\n"  # noqa: E501
            f"OUV|Balance initiale|OUVERTURE/2020|20200101|121000|Account Receivable|{self.partner_a.id}|partner_a|-|20200101|/| 000000000003000,00|0,00|||20200101||\r\n"  # noqa: E501
            f"INV|Customer Invoices|INV/2020/00001|20200101|121000|Account Receivable|{self.partner_a.id}|partner_a|-|20200101|INV/2020/00001| 000000000003000,00|0,00|||20200101| 000000000003000,00|USD\r\n"  # noqa: E501
            "INV|Customer Invoices|INV/2020/00001|20200101|400000|Product Sales|||-|20200101|test line|0,00| 000000000003000,00|||20200101|-000000000003000,00|USD",  # noqa: E501
        )
