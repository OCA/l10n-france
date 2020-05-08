On the customers that you invoice via Chorus, you must:

* enter their *SIRET* (*Accounting* tab),
* select *Chorus* as *Customer Invoice Transmission Method* (*Accounting* tab),
* select the *Info Required for Chorus* to the value that you obtained from Chorus (menu *Rechercher Structure Publique*),
* if the service is a required information for that customer in Chorus, you must create the Chorus service and then create an invoicing contact and select the related *Chorus Service* and make sure that this contact is used as *Customer* on the invoice.

If you want to use the Chorus API to easily send invoices to Chorus from Odoo, you must:

* edit the Odoo server configuration file and add two keys *chorus_api_oauth_id* and *chorus_api_oauth_secret* that contain your Oauth client ID and client secret obtained via `PISTE <https://developer.aife.economie.gouv.fr/>`_. Don't forget to restart the Odoo server after the update of its configuration file.

* in the menu *Accounting > Configuration > Settings*, in the section *Chorus API*, enable the option *Use Chorus API*, which will add all users to the *Chorus API* group. Then set the additional configuration parameters for Chorus API that will be prompted on the settings page.

In the menu *Settings > Technical > Automation > Scheduled Actions*, you should also activate the 3 scheduled actions related to Chorus Pro.
