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
