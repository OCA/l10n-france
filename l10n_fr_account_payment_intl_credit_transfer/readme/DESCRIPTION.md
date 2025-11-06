This module adds the regulatory reporting codes used in France for the
generation of non-SEPA ISO 20022/PAIN credit transfer files.
These codes are defined in the [technical note DGS
n°16-02](https://www.banque-france.fr/system/files/2023-08/banque_de_france_espace_declarants_note_technique_dgs_ndeg_16-02_v1.1.pdf)
of the [Banque de France](https://www.banque-france.fr/).

These regulatory codes are required for non-SEPA credit transfers with
an amount over 50 000 € (or equivalent amount in another currency).

This module allows to define a default regulatory reporting code on partners, that will be used by default on the non-SEPA credit transfer payment lines of this partner.
