.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

======================
MIS reports for France
======================

This modules provides MIS Builder Report templates for the French
P&L and Balance Sheet taking the liasse fiscale and liasse fiscale simplifiée
as reference.

Installation
============

This module depends on the *mis_builder* module, which is available in the OCA project `account-financial-reporting <https://github.com/OCA/account-financial-reporting>`_.

Configuration
=============

To configure this module, you need to go to
*Accounting > Reporting > MIS Reports* and create a report instance
according to the desired time periods and using one of the following
templates provided by this module:

* Compte de résultat (FR - liasse fiscale)
* Compte de résultat (FR - liasse fiscale simplifiée)
* Bilan (FR - liasse fiscale)
* Bilan (FR - liasse fiscale simplifiée)

To obtain correct results, the account codes prefixes must match the official
French chart of accounts.

Usage
=====

To use this module, you need to go to
*Accounting > Reporting > MIS Reports* and use the buttons
available on the previously configured reports such as Preview,
Print, Export, Add to dashboard.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/121/8.0

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/l10n-france/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/l10n-france/issues/new?body=module:%20l10n_fr_mis_reports%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Credits
=======

Contributors
------------

* Alexis de Lattre <alexis.delattre@akretion.com>

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose mission is to support the collaborative development of Odoo features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
