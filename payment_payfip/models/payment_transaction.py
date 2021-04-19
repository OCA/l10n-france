# Copyright 2021 Moka Tourisme
# @author: Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime
from odoo import api, models, fields
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare

import logging
_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    @api.model
    def _payfip_form_get_tx_from_data(self, data):
        """
        Given a data dict coming from PayFIP, verify it and find the related
        transaction record.
        """
        reference = data.get("refdet")
        # Sanity Checks
        if not reference:
            error_msg = (
                "PayFIP: Received data with missing reference (%s)" % reference
            )
            _logger.info(error_msg)
            _logger.debug(data)
            raise ValidationError(error_msg)
        # Try to find tx
        tx = self.search([("reference", "=", reference)])
        if not tx or len(tx) > 1:
            error_msg = (
                "PayFIP: Received data for reference %s" % reference
            )
            if not tx:
                error_msg += "; No order found"
            else:
                error_msg += "; Multiple orders found"
            _logger.info(error_msg)
            _logger.debug(data)
            raise ValidationError(error_msg)
        return tx

    @api.multi
    def _payfip_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        # Check acquirer reference
        if self.acquirer_reference and data.get('numauto') != self.acquirer_reference:
            invalid_parameters.append(
                ("Transaction Id", data.get("numauto"), self.acquirer_reference)
            )
        # Check amount
        amount = data.get("montant", "000")
        amount = "%s.%s" % (amount[:-2], amount[-2:])
        amount = float(amount)
        if float_compare(amount, self.amount, 2) != 0:
            invalid_parameters.append(
                ("Amount", data.get("montant"), "%.2f" % self.amount)
            )
        return invalid_parameters

    @api.multi
    def _payfip_form_validate(self, data):
        status = data.get("resultrans")
        res = {
            "acquirer_reference": data.get("numauto"),
            "date": fields.Datetime.now(),
        }
        # P: Payée CB
        # V: Payée Prélèvement
        if status in ["P", "V"]:
            res["date"] = datetime.strptime(
                "%s %s" % (data.get("dattrans", ""), data.get("heurtrans", "")),
                "%d%m%Y %H%M"
            )
            self._set_transaction_done()
        else:
            self._set_transaction_cancel()
        return self.write(res)
