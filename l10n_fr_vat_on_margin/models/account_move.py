from odoo import models, fields, api
from odoo.tools import frozendict, formatLang, format_date, float_compare, Query


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _find_and_set_purchase_orders(self, po_references, partner_id, amount_total, prefer_purchase_line=False,
                                      timeout=10):
        # hook to be used with purchase, so that vendor bills are sync/autocompleted with purchase orders
        print("Hello from _find_and_set_purchase_orders")
        self.ensure_one()

    def _link_invoice_origin_to_purchase_orders(self, timeout=10):
        print("=== _link_invoice_origin_to_purchase_orders ===", self)
        for move in self.filtered(lambda m: m.move_type in self.get_purchase_types()):
            print('=== move ===', move)
            references = [move.invoice_origin] if move.invoice_origin else []
            print("=== references ===", references)
            move._find_and_set_purchase_orders(references, move.partner_id.id, move.amount_total, timeout=timeout)
        return self
