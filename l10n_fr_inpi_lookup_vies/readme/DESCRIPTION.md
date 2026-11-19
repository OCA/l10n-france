This module depends on and enhances the l10n_fr_inpi_lookup module.
It adds the compute of a theoretical VATnumber from the SIREN and then checks the
validity of the VAT number (depending on configuration) on
[VIES](https://ec.europa.eu/taxation_customs/vies/) (if invalid, the VAT
number is discarded).

This module add vat and vies_valid to the l10n_fr_inpi_lookup fields
