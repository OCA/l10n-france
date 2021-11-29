Under the menu *Invoicing > Configuration > Settings*, in the *France VAT* section, you must configure:

* the company bank account that will be used as the default bank account to pay VAT,
* the email (login) corresponding to your account in Teledec.fr
* select the legal representative of your company. This person must have a name, an email, a function and a title (mister or madam).
* the Company Legal Form (select in the list),
* Teledec Test Mode: if enable, the VAT returns will be sent to the Teledec staging server and the VAT returns will not relayed to DGFiP.

In the Odoo Server configuration file, add an entry **teledec_private_key** with the private key that was sent to your by Teledec.
