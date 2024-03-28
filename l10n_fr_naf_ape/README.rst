.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==========================================
French NAF partner categories and APE code
==========================================

This module imports the French official NAF
nomenclature of partner activities as partner categories, as an extension to
the NACE categories of the European Union.

It will also add a field to the partner form, to enter the partner's APE
(official main activity of the company), picked among the NAF nomenclature.

Installation
============

Because the NAF is based on the NACE of the European Union, this module
depends on the categories provided by the module `l10n_eu_nace`.
To install this module, you may either:

* download it from the Odoo app store: https://www.odoo.com/apps?search=l10n_eu_nace
* OR download and install the code of the OCA project *Community data files*: https://github.com/OCA/community-data-files

Usage
=====

Each NAF code is represented by a partner category.
For convenience, the NAF can be entered either in the main partner "tag" fields, or in a dedicated field called "APE" on the partner form.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/121/10.0

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

* Lionel Sausin (Numérigraphe) <ls@numerigraphe.com>

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
