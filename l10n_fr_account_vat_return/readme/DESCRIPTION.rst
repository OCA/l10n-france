This module adds support for the French VAT declaration *CA3* (monthly or quarterly):

* computation of the boxes of the CA3 form,
* print the CA3 PDF,
* generate the corresponding journal entry.

It can also be used for the smaller companies which have a yearly CA12 VAT declaration. But, for CA12, the generation of the PDF and the auto-fill of the form on impots.gouv.fr is not supported: you will have to manually copy the values on the online by finding, for each CA3 box, the equivalent box in the CA12.

This module also supports:

* declaration 3519 for the reimbursement of VAT credit,
* declaration 3310-A (CA3 Appendix) for the additional taxes

For the CA3 Appendix, the taxes that target few large companies such as taxe sur les sociétés d'autoroute, taxe sur les éoliennes en mer, taxe sur le débarquement de passagers en Corse, taxe sur les services numériques i.e. taxe GAFA,... are not maintained any more because it is a waste of time. If you need one of them, you can create the related boxes manually in the configuration menu.
