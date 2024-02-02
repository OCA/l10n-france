# Copyright 2024 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestFrDas2(TransactionCase):
    def test_street(self):
        test_map = {
            "": "0000                            ",
            " 7 rue Henri Rolland ": "0007  RUE  Henri Rolland        ",
            "27, rue Henri Rolland": "0027  RUE  Henri Rolland        ",
            "27,rue Henri Rolland": "0027  RUE  Henri Rolland        ",
            "55A rue du Tonkin": "0055A RUE  du Tonkin            ",
            "55 A rue du Tonkin": "0055A RUE  du Tonkin            ",
            "55.A rue du Tonkin": "0055A RUE  du Tonkin            ",
            "55AB rue du Tonkin": "0055       AB rue du Tonkin     ",
            "35bis, rue Montgolfier": "0035B RUE  Montgolfier          ",
            "35 bis, rue Montgolfier": "0035B RUE  Montgolfier          ",
            "35BIS, rue Montgolfier": "0035B RUE  Montgolfier          ",
            "35 BIS rue Montgolfier": "0035B RUE  Montgolfier          ",
            "27ter, rue René Coty": "0027T RUE  René Coty            ",
            "27 Quarter rue René Coty": "0027Q RUE  René Coty            ",
            "1242 chemin des Bauges": "1242  CHE  des Bauges           ",
            "12242 RD 123": "0000       12242 RD 123         ",
            "122 rue du Général de division Tartempion": "0122  RUE  e division Tartempion",
            "Kirchenstrasse 177": "0000       Kirchenstrasse 177   ",
            "Place des Carmélites": "0000  PL   des Carmélites       ",
            "123 Bismark avenue": "0123       Bismark avenue       ",
            "42, avenue des Etats-Unis": "0042  AV   des Etats-Unis       ",
            "455 quai Arloing": "0455  QUAI Arloing              ",
            "route nationale 13": "0000  N    13                   ",
            "34 av. Barthelemy Buyer": "0034  AV   Barthelemy Buyer     ",
            "34 av Barthelemy Buyer": "0034  AV   Barthelemy Buyer     ",
            "4 bld des Belges": "0004  BD   des Belges           ",
            "4 bd des Belges": "0004  BD   des Belges           ",
            "12 allée des cavatines": "0012  ALL  des cavatines        ",
            "12 all.  des cavatines": "0012  ALL  des cavatines        ",
            "7 montée des soldats": "0007  MTE  des soldats          ",
        }

        for street, result in test_map.items():
            self.assertEqual(len(result), 32)
            res = self.env["l10n.fr.das2"]._prepare_street(street)
            self.assertEqual(res, result)
