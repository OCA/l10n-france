Déclaration d'Échange de Biens (DEB)
====================================

This module adds support for the *Déclaration d'Échange de Biens* (DEB) for France.

More information about the DEB is available on this `official web page <http://www.douane.gouv.fr/articles/a10897-notions-essentielles-sur-la-declaration-d-echanges-de-biens>`.

Configuration
=============

To configure this module, you need to:

 * go to the menu Accounting > Configuration > Miscellaneous > Intrastat Types to create/verify the Intrastat Types
 * go to the menu Settings > Companies > Companies, edit the current company and go to the *Intrastat Settings* tab

If your obligation level is *detailed*, you need to add your user to the corresponding group and configure the department code on your higher-level internal stock locations.

Make sure that you have already configured the other modules *intrastat_base* and *intrastat_product* on which this module depend.

WARNING: there are A LOT of settings for DEB and all these settings need to be configured properly to generate DEBs with Odoo.

Usage
=====

To use this module, you need to go to the menu Accounting > Reporting > Legal Reports > Intrastat Reporting > Intrastat Product and create a new DEB. Depending on your obligation levels, you may have to create 2 DEBs: one for export (Expéditions) and one for import (Introductions). Then, click on the button *Generate lines from invoices* to automatically generate the lines of DEB. After checking the lines that have been automatically generated, click on the button *Attach XML file* to create the XML file corresponding to the DEB. Eventually, connect to your account on `pro.douane <https://pro.douane.gouv.fr/>` and upload the DEB XML file.

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
