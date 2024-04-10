# Copyright 2024 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from urllib.parse import parse_qs

from odoo.addons.payment.tests.common import PaymentCommon


def from_qs(qs):
    return {k: v[0] for k, v in parse_qs(qs).items()}


class MoneticoCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.monetico = cls._prepare_provider(
            "monetico",
            update_values={
                "monetico_ept": "1234567",
                "monetico_company_code": "company_1",
                "monetico_secret": "12345678901234567890123456789012345678P0",
            },
        )

        # Override default values
        cls.provider = cls.monetico
        cls.currency = cls.currency_euro

        cls.notification_data = from_qs(
            "TPE=1234567"
            "&date=05%2f12%2f2006%5fa%5f11%3a55%3a23"
            "&montant=62%2e75EUR"
            "&reference=Test Transaction"
            "&MAC=7417aa7b471dba7401e02660f1973213329d39de"
            "&texte-libre=LeTexteLibre"
            "&code-retour=paiement"
            "&cvx=oui"
            "&vld=1208"
            "&brand=VI"
            "&status3ds=1"
            "&numauto=010101"
            "&originecb=FRA"
            "&bincb=12345678"
            "&hpancb=74E94B03C22D786E0F2C2CADBFC1C00B004B7C45"
            "&ipclient=127%2e0%2e0%2e1"
            "&originetr=FRA"
            "&modepaiement=CB"
            "&veres=Y"
            "&pares=Y"
        )

        cls.error_data = from_qs(
            "TPE=9000001"
            "&date=05%2f10%2f2011%5fa%5f15%3a33%3a06"
            "&montant=1%2e01EUR"
            "&reference=Test Transaction 2"
            "&MAC=DE96CB30E9239E2D5AE03063799C9B76F3F9FA60"
            "&textelibre=Ceci+est+un+test%2c+ne+pas+tenir+compte%2e"
            "&code-retour=Annulation"
            "&cvx=oui"
            "&vld=0912"
            "&brand=MC"
            "&status3ds=-1"
            "&motifrefus=filtrage"
            "&originecb=FRA"
            "&bincb=12345678"
            "&hpancb=764AD24CFABBB818E8A7DC61D4D6B4B89EA837ED"
            "&ipclient=10%2e45%2e166%2e76"
            "&originetr=inconnue"
            "&modepaiement=CB"
            "&veres="
            "&pares="
            "&filtragecause=4-"
            "&filtragevaleur=FRA-"
        )
