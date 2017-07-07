.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===========================================
L10n France Certification - Abstract module
===========================================

This module extends the functionality of base module to feat with
the french Sapin law.

This 8.0 module is a backport of l10n_fr_certification of Odoo SA, made on Odoo
9.0 Community Edition.

Technical and Migration Note
============================

The 9.0 module has been backported, and refactored into two modules and a third
one is created for Point Of Sale.

* l10n_fr_certification_abstract, that provide generic feature. (around sha1)
  to be used in extra other modules like l10n_fr_certification_pos.
  This module provides three new abstract models:
    * certification.sequence.holder.mixin that creates on a defined model
      a new ir.sequence (type no_gap) if the model is associated to a french
      company.
    * certification.model.mixin that provides functions to generate a hash
      for a certified model.
    * certification.model.line.mixin that provides extra features to
      generate a hash.


* l10n_fr_certification_account:
    * account.move overloads certification.model.mixin model.
    * account.move.line overloads certification.model.line.mixin model.
    * res.company overloads certification.sequence.holder.mixin model.

* l10n_fr_certification_pos:
    * pos.order overloads certification.model.mixin model.
    * pos.order.line overloads certification.model.line.mixin model.
    * pos.config overloads certification.sequence.holder.mixin model.


When you'll migrate your database into 9.0+ version, the present module
could be replaced by the official one, and you could uninstall
l10n_fr_certification_account module. (and l10n_fr_certification_abstract,
if you don't use this module for PoS, or other future uses)

Important Notes
===============

This modules disable some button and views.

A person who wishes to falsify his accounting datas

* will not have the possiblity to do it by the UI, neither by XML-RPC Calls.
* will corrupt the hashes, if he tries to do it by SQL requests.

A person who would have access to the system will have the possibility to
disables the protections provided by this modules. (Source Code and
Odoo configuration file)

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/121/8.0

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/pos/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Sylvain LE GAL (https://twitter.com/legalsylvain)

Funders
-------

The development of this module has been financially supported by:

* Akrétion (http://www.akretion.com)
* GRAP, Groupement Régional Alimentaire de Proximité (http://www.grap.coop)

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
