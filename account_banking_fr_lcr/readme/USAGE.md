This module adds a new field *Bill of Exchange Bank Account* on customer
invoices to select the bank account of the customer that will be debited
by the letter of exchange. This bank account must be a french IBAN.

If you configured the payment mode for **Accepted Letter of Change**,
you will have a button *Print Bill of Exchange* on customer invoices to
get the letter of change as PDF.

This module uses the standard workflow of debit orders as implemented in
the OCA module **account_payment_batch_oca**. A debit order linked to a
payment mode with the payment method *Lettre de change relevé* has a few
additionnal constraints:

- all payment lines must be in euro currency,
- the bank accounts on the payment lines must be french IBANs,
- if the payment order is configured with cash discount, you must
  configure the value date on the payment order (new field added by this
  module).
