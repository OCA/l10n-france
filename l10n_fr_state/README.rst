.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=======================
French States (Régions)
=======================

This module populate the table *res_country_state* with the french
states (*Régions françaises*), including overseas states (in order to
have the full list of legal French Regions in the l10n_fr_state table).

In the past, the module was using 3166-2:FR codifications
without country prefix (more detail on `Wikipedia
<http://fr.wikipedia.org/wiki/ISO_3166-2:FR>`_), but unfortunately it is
not the codification used by `geonames.org <http://www.geonames.org/>`_.
So, to be compatible with the OCA module *base_location_geonames_import*
which is available in the OCA project `partner-contact
<https://github.com/OCA/partner-contact>`_, we switched to the
codification used by geonames.

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/121/9.0


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

* Sylvain LE GAL (`Twitter <https://twitter.com/legalsylvain>`_), GRAP (Groupement Régional Alimentaire de Proximité)
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
