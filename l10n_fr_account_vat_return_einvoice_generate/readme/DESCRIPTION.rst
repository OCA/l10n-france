This is a glue module between **l10n_fr_account_vat_return** and **account_einvoice_generate**.

When this module is installed, Odoo will set the UNECE Due Date Type Code for tax exigibility in the invoice's XML file from the boolean field **out_vat_on_payment** of the invoice (field added by the module *l10n_fr_account_vat_return*) instead of the native field **tax_exigibility** of the tax.
