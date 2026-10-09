This small module adds support several France-specific features of the OCA module **account_invoice_import** of the [edi OCA project](https://github.com/OCA/edi):

- partner matching based on SIREN,
- support SIREN and SIRET in the wizard that allows to create or update a partner when no partner has been matched during the import of the invoice,
- matching of incoterms upon invoice import using EXT-FR-FE-185 and EXT-FR-FE-186,
- if the OCA module **l10n_fr_account_oca** is installed, it will automatically set the fiscal position configured for VAT on payment french suppliers when BT-8 has the value for VAT on payment.
