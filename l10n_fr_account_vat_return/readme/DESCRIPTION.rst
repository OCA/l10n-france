This module adds support for the French VAT declaration *CA3* (monthly or quarterly):

* computation of the boxes of the CA3 form,
* print the CA3 PDF,
* auto-fill the CA3 form on impots.gouv.fr,
* generate the corresponding journal entry.

It can also be used for the smaller companies which have a yearly CA12 VAT declaration. But, for CA12, the generation of the PDF and the auto-fill of the form on impots.gouv.fr is not supported: you will have to manually copy the values on the online form.

This module also supports declaration 3519 for the reimbursement of VAT credit.

AFAIK, this module is the only solution which proposes a free tele-transmission of the CA3 via the auto-fill of the CA3 form on impots.gouv.fr. All the other CA3 tele-transmission solutions are not free. For that, this module relies on `Selenium IDE <https://www.selenium.dev/selenium-ide/>`_, which is a plugin available for Firefox and Chrome. Selenium is a free-software project initially designed to test Websites.

The following boxes of the CA3 form are natively supported by this module:

* 04: **Exportations hors CE** : Odoo selects the *Extra-EU* fiscal positions, gets the destination account of the account mapping and sums the period balance of each destination account.
* 5A: **Ventes à distance taxables dans un autre État membre au profit des personnes non assujetties – Ventes B to C**: Odoo selects the *Intra-EU B2C over 10k€ limit* fiscal positions, gets the destination account of the account mapping and sums the period balance of each destination account.
* 06: **Livraisons intracommunautaires à destination d'une personne assujettie - Ventes B to B**: Odoo selects the *Intra-EU B2B* fiscal positions, gets the destination account of the account mapping and sums the period balance of each destination account.
