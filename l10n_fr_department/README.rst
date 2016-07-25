.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=================================
French Departments (Départements)
=================================

This module creates a new model *res_country_department*, sub
division of the *res_country_state* and populate it with all the
french departments, but only the french departments of mainland.
If you need the overseas departments, please install the module
*l10n_fr_department_oversea*.

It also adds a computed many2one *department_id* field on the
*res_partner* object (this field is not displayed in the partner form
view by default).

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
