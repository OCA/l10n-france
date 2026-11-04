This module has been created in order to implement the changes needed in UBL/CII/Factur-x
formats for France, in particular in the context of e-invoicing starting in September 2026.

Odoo has implemented a full module for this purpose : l10n_fr_pdp

The problem of that module is that it is written in order to interact with Odoo as IAP server
interfacing with France authorities.

Many Odoo users will not use Odoo IAP server and therefore need XML invoices without the full
l10n_fr_pdp module which also forces the installation of other modules like account_peppol(_*)
or TOTP.

We proposed to Odoo to split the module in 2 but they replied that although it was not planned (see <https://github.com/odoo/odoo/pull/268822>),
it should not be done this way but rather adding the necessary changes directly in account_edi_ubl_cii

Since we do not know when this may happen, we start this module to implement required changes
on XML generation / import for France.

This modules depends only on Odoo core (Community Edition) modules :
* l10n_fr_account (which depends on l10n_fr and account, base_iban and base_vat)
* account_edi_ubl_cii_tax_extension (which depends on acconut_edi_ubl_cii)
