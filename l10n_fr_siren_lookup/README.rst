.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3


=======================================================
Retrieve partner information from French SIREN database
=======================================================

Description
===========

This modules looks for address and contact information for a company into `SIRENE database <https://data.opendatasoft.com>`

A button is added in Contact form, which creates a wizard that would update the following information:

* Company Name
* Address
* Postal Code
* City
* Legal Type
* SIREN & SIRET
* APE Code and label
* Creation date
* # Staff
* Company Category
* Date and label for ESS (Economie Sociale et Solidaire)

This module relies on `INSEE's API <https://data.opendatasoft.com/api/records/1.0/search/>`

Usage
=====

A button "Pre-Fill / Update" is added on company form views.

By default, the search field is filled with Company name. To get more accurate results, you may want to add the City name where the company is registered then click on "Search"

A list of company is proposed. You may want to click on one in order to see corresponding information or directly selecting company from treeview. Once a company is selected, wizard goes away and corresponding company information are added/updated in "Legal Infos" page from NoteBook.


Credits
=======

Contributors
------------

* Benjamin Rivier <benjamin-filament>
* Remi Cazenave <remi-filament>


Maintainer
----------

.. image:: https://le-filament.com/images/logo-lefilament.png
   :alt: Le Filament
   :target: https://le-filament.com

This module is maintained by Le Filament
