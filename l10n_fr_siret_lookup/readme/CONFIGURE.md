You can use this module without configuration.

However 2 configuration parameter can be adjusted in *Invoicing* > Configuration > Settings :
- **Verify VAT Numbers** (vat_check_vies field from base_vat module): this parameter will define whether you want check computed VAT number against EU VIES validation service
- **Force VAT Numbers during SIRET Lookups if VIES check times out or is disabled** (force_vat_siret_lookup): this parameter allows to force use of computed VAT number even if not checked agains EU VIES validation service or if an Exception is raised by EU VIES validation (for instance because of Timeout, which are quite frequent while checking for FR VAT)

The 2 above parameters are company dependent.

*Note:* if EU VIES validation service reports that VAT number is incorrect, the VAT field is emptied (even if Force... parameter is ticked)
