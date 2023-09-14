This module adds support for the French VAT declaration *CA3* (monthly or quarterly):

* computation of the boxes of the CA3 form,
* print the CA3 PDF,
* generate the corresponding journal entry.

It can also be used for the smaller companies which have a yearly CA12 VAT declaration. But, for CA12, the generation of the PDF and the auto-fill of the form on impots.gouv.fr is not supported: you will have to manually copy the values on the online by finding, for each CA3 box, the equivalent box in the CA12.

This module also supports:

* declaration 3519 for the reimbursement of VAT credit,
* declaration 3310-A (CA3 Appendix) for the additional taxes.
