Apply French Chart of Account to main company when installed before `account` module.
To achieve this target, we set FR country `base.main_company` on partner.
This is especially useful when using `l10n_fr_account_oca`, so the French Chart of Account
installs right at database initialization instead.

Since v20, `country_fr` is strictly equivalent of a new argument of Odoo CLI: `--country FR`.
So you only need `country_fr` if you cannot use this argument, for example due to automations
in your infrastructure.

Note: `country_fr` has no effect if `account` module is already installed.
