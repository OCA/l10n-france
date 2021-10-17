This modules updates partner fields via the `SIRENE database <https://data.opendatasoft.com>`. It uses the dataset *economicref-france-sirene-v3* of `opendatasoft <https://public.opendatasoft.com/explore/dataset/economicref-france-sirene-v3/information/>`. It computes a theorical VAT number from the SIREN and then checks the validity of the VAT number on `VIES <https://ec.europa.eu/taxation_customs/vies/>`_ (if invalid, the VAT number is discarded).

The module supports 2 scenarios:

* update of an existing partner via the menu *Action > SIREN Lookup*,
* creation of a new partner: start by setting the VAT number field, the SIREN field or SIRET field and Odoo will set the other fields. For usability purposes, it also work when you write the VAT number, SIREN or SIRET in the company name field.

In the 2 scenarios, it will update the following fields:

* Company Name
* Street
* Postal Code
* City
* Country
* SIREN and NIC (i.e. SIRET)
* VAT Number
* Language (creation scenario only)
