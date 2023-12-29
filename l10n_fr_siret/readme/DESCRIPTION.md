The **l10n_fr** module from the official addons adds a *SIRET* field on
partners, but it doesn't verify its validity. This module
**l10n_fr_siret** adds several features:

- the validity of the SIRET is checked using its checksum.
- it adds **SIREN** and **NIC** fields (reminder: SIREN + NIC = SIRET).
  If you enter the SIRET, these 2 fields are automatically computed from
  SIRET.
- multi-site companies have a single SIREN and one SIRET per site i.e.
  one NIC per site. This module allows to enter a specific NIC on child
  partners.
- it adds a warning banner on the partner form view if another partner
  has the same SIREN.

![](static/description/partner_duplicate_warning.png)
