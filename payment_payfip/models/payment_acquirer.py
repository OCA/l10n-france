# Copyright 2021 Moka Tourisme
# @author: Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
import uuid
from odoo import api, models, fields
from werkzeug import urls


class PaymentAcquirer(models.Model):
    _inherit = "payment.acquirer"

    provider = fields.Selection(
        selection_add=[('payfip', 'PayFIP')],
    )
    payfip_clientid = fields.Char(
        string="Client ID",
        required_if_provider="payfip",
        groups="base.group_user",
    )

    @api.multi
    def payfip_form_generate_values(self, values):
        # PayFIP won't allow special characters in their refdet field
        # So we change the tx.reference to something PayFIP can handle
        # It's also limited to 30 characters only
        tx = self.env['payment.transaction'].search(
            [('reference', '=', values.get('reference'))],
        )
        if tx.state not in ['done', 'pending']:
            tx.reference = str(uuid.uuid4()).replace("-", "")[:30]
        # Prepare values
        payfip_values = dict(values)
        payfip_values.update({
            "numcli": self.payfip_clientid,
            "exer": fields.Date.today().year,
            "refdet": tx.reference,
            "objet": re.sub('[^a-zA-Z0-9]', '', values.get("reference"))[:100],
            "montant": int(values.get("amount", 0.00) * 100),
            "mel": (
                values.get('partner_email')
                or values.get('billing_partner_email')
                or ''
            ),
            "urlcl": urls.url_join(self.get_base_url(), "/payment/payfip/return"),
            "saisie": "X" if self.environment == "prod" else "T",
        })
        return payfip_values

    @api.multi
    def payfip_get_form_action_url(self):
        return "https://www.tipi.budget.gouv.fr/tpa/paiement.web"
