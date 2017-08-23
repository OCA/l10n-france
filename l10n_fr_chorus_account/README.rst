.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

======================
L10n FR Chorus Account
======================

This is the base module for the support of Chorus. Chorus specifications are available on `Chorus Pro Community website <https://communaute-chorus-pro.finances.gouv.fr/>`_. Chorus Pro is the electronic invoicing plateform of the French administration. All the suppliers of the French administration can send their invoices through Chorus and it is progressively becoming an obligation for all suppliers. To know more about Chorus and the obligation to send electronic invoices to the French administration, read `the dedicated page <https://www.economie.gouv.fr/entreprises/marches-publics-facture-electronique>`_ on the website of the Ministry of Economic Affairs.

To be able to generate an electronic invoice for Chorus, you need the module *l10n_fr_chorus_ubl* (or other modules that support a specific e-invoice format).

Configuration
=============

On the customers that you invoice via Chorus, you must:

* enter their *SIRET* (*Accounting* tab),
* select *Chorus* as *Customer Invoice Transmission Method* (*Accounting* tab),
* select the *Info Required for Chorus* to the value that you obtained from Chorus (menu *Rechercher Structure Publique*),
* if the service code is a required information for that customer in Chorus, create an invoicing contact and enter the related *Chorus Service Code* and make sure that this contact is used as *Customer* on the invoice.

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/121/10.0

Known issues / Roadmap
======================

Add support for the automatic transmission of invoices to Chorus via API (but it requires a RGS 1 star certificate, which costs about 250 € / year).

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/l10n-france/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Contributors
------------

* Alexis de Lattre <alexis.delattre@akretion.com>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.
