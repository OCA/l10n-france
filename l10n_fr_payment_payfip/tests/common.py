# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.payment.tests.common import PaymentCommon


class PayFIPCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_fr.l10n_fr_pcg_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.payfip = cls._prepare_provider('payfip', update_values={
            'payfip_customer_number': '006382',
            'payfip_form_action_url': "https://www.tipi.budget.gouv.fr/tpa/paiementws.web",
        })

        # Override default values
        cls.provider = cls.payfip
        cls.currency = cls.currency_euro
