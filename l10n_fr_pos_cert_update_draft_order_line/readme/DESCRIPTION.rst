This module fixes the Odoo module 'French Point of Sale Certification'
to allow cashier to update order lines, when order is **not** confirmed.

* The law stipulates that the tool must not be used to modify confirmed orders,
  but does not specify that it is forbidden to change a quantity if the order
  is in the process of being seized.

* If the cashier make a mistake, the current Odoo design generates hugly and
  incomprehensible tickets for the customer.

* In fact, Odoo core module is totally inconsistent in its understanding of the law,
  since it prohibits the modification of a line in a draft order,
  but authorizes the deletion of the full draft order.
