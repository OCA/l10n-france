The module **l10n_fr** from the official addons uses the field *company_registry*
on partners as *SIRET*, but it doesn't verify its validity. This module
**l10n_fr_siret** adds several features for French partners:

- the string of the field is updated from *SIRET* to **SIREN or SIRET**,
- the validity of the SIREN and/or SIRET is checked using its checksum,
- it checks the consistence between the VAT number and SIREN,
- it checks that parent and child partners have the same SIREN,
- it adds a warning banner on the partner form view if another partner
  has the same SIREN.

![Partner form view with warning banner](static/description/partner_duplicate_warning.png)
