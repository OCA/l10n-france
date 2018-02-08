.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=======================
French States (Régions)
=======================

This module populate the table *res_country_state* with the french
states (*Régions françaises*), but only the french states of mainland.
If you need the overseas states, please install the module
*l10n_fr_department_oversea*.

In the past, the module was using 3166-2:FR codifications
without country prefix (more detail on `Wikipedia
<http://fr.wikipedia.org/wiki/ISO_3166-2:FR>`_), but unfortunately this
codification hasn't been updated since 2013, so we can't
use it with the new organisation of regions that was introduced on January 1st 2016. So we switched to
the INSEE codification, cf `Wikipedia (Codes_géographiques_de_la_France) <https://fr.wikipedia.org/wiki/Codes_g%C3%A9ographiques_de_la_France>`_ ; by the way, this codification is also used by `geonames.org <http://www.geonames.org/>`_.

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/121/11.0

Known issues / Roadmap
======================

* YML data should be migrated to XML

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
* Nicolas JEUDY <https://github.com/njeudy>

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
