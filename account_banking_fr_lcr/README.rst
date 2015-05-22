French Letter of Change
=======================

This module adds support for French Letters of Change (in French :
Lettre de Change Relevé aka LCR).

This payment type is still in use in France and it is *not* replaced by SEPA
one-off Direct Debits.

With this module, you can generate an LCR CFONB file to send to your bank.

Configuration
=============

To configure this module, you need to create a new payment mode linked
to the payment type *Lettre de Change Relevé* that is automatically
created when you install this module.

Usage
=====

To use this module, you need to create a new Direct Debit Order and
select the LCR payment mode.


Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/l10n-france/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/l10n-france/issues/new?body=module:%20account_banking_fr_lcr%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.


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
