This module creates a new model *res_country_department*, sub
division of the *res_country_state* and populate it with all the
french departments, but only the french departments of mainland.
If you need the overseas departments, please install the module
*l10n_fr_department_oversea*.

It also adds a computed many2one *department_id* field on the
*res_partner* object (this field is not displayed in the partner form
view by default).
