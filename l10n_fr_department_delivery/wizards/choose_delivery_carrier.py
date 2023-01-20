from odoo import api, models


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = "choose.delivery.carrier"

    @api.depends("partner_id")
    def _compute_available_carrier(self):
        super()._compute_available_carrier()
        partner = self.order_id.partner_shipping_id
        for rec in self:
            available_carrier_ids = \
                rec.available_carrier_ids.filter_carrier_with_departments(
                    partner
                )
            rec.available_carrier_ids = available_carrier_ids
