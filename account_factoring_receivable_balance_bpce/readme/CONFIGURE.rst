- use a company with l10n_fr
- alternatively you may create a new one with

Here you can create a new company with BPCE settings for default currency


.. code-block:: python

   env["res.company"]._create_french_company(company_name="my new company")


Here you may create settings for a new installed currency

.. code-block:: python

   env.browse(mycompany_id)._configure_bpce_factoring(currency_record)


- you may execute this last method with UI in res.company form (Factor tab)

- now you can go to journals and filter them with `Factor type`.

- set bpce to Factor Type to each bank journal related to currency of previous journals.
