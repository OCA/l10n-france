This module provides the chart of accounts, taxes and fiscal positions
for companies based in France mainland. It doesn't apply to companies
based in the DOM-TOMs (Guadeloupe, Martinique, Guyane, Réunion, Mayotte,
etc.).

This module is a fork of the **l10n_fr_account** module from the official
addons. The decision to maintain a fork was taken after the merge of
this huge [pull request](https://github.com/odoo/odoo/pull/84918) on
Odoo version 14.0 on October 6th 2022. This pull request increased the
number of taxes to 67 (!) and suffer the contrains of the VAT module of
Odoo Enterprise. It broke 2 OCA modules: **l10n_fr_account_tax_unece**
and the test suite of **l10n_fr_account_vat_return**.

The goals of the fork are:

- provide a reasonable number of taxes (35 taxes, compared to 67 which
  is about half the number of taxes provided by the **l10n_fr_account** module
  !),
- provide a clean and up-to-date chart of account for France (up-to-date
  with official chart of account of the [ANC](https://www.anc.gouv.fr/)
  published on January 1st 2025),
- provide taxes, fiscal positions and a chart of accounts properly
  configured for the OCA module **l10n_fr_account_vat_return**, the
  opensource VAT module for France,
