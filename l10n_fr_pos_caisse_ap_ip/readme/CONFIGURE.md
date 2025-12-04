In the menu *Point of sale \> Configuration \> Payment Methods*, on the
payment method that correspond to a payment by card:

- select the appropriate journal, which should be a bank journal (and
  not a cash journal, otherwise the field *Integrate with* is
  invisible)
- field *Integration*: selection **Terminal**
- field *Integrate with*: select **Caisse AP over IP (France
  only)**
- field *Caisse-AP Payment Terminal IP Address*: set the IP address of
  the payment terminal,
- field *Caisse-AP Payment Terminal Port*: set the TCP port of the
  payment terminal (8888 by default),
- field *Payment Mode*: set *Card* (the value *Check* is for the *Check*
  payment method if you use a check printer connected to the payment
  terminal such as Ingenico i2200)
