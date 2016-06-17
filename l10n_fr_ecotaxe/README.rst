.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License


This module manages the Ecotaxe (Recycling Tax) for France.
==========================================================

This module applies to companies based in France mainland. It doesn't apply to
companies based in the DOM-TOMs (Guadeloupe, Martinique, Guyane, Réunion,
Mayotte).

This localisation module add a field "is Ecotaxe" on Tax object.
It add Ecotaxe amount on sale line, purchase line and invoice line. 	
furthermore, a total ecotaxe are added at the footer of each document.
The fields "Untaxed amount include Ecotaxe amount" was added for readability.

To make easy ecotaxe management and to factor the data, ecotaxe are set on products via ECOTAXE classification.
ECOTAXE classification can either a fixed or weight based ecotaxe.
On the taxe "Ecotaxe" we use python code to get a right ecotaxe
value from product.
One ecotaxe can be used for all products.
You should define two ecotaxes :
* sale ecotaxe
* purchase ecotaxe


Setting
=============

Add sale and purchase ecotexe. The Ecotaxe amount must be included in base of VAT. The ecotaxe should have a sequence less then VAT. Define the right account on Ecotaxe.
Add ecotaxe classification via the menu *Accounting > configuration > Taxes >  Ecotaxe Classification.

Assign ecotaxe to a product.


Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/l10n-france/issues>


Credits
=======

Contributors
------------

* Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>


Maintainer
----------
.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose mission is to support the collaborative development of Odoo features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.


