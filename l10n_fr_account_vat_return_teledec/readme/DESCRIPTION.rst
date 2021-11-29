This module adds support for EDI teletransmission of the VAT return via `Teledec.fr <https://www.teledec.fr/>`_. As explained on `this page <https://www.impots.gouv.fr/portail/international-professionnel/questions/comment-proceder-la-teledeclaration-selon-la-procedure-edi>`_ of impots.gouv.fr, you have to select an EDI partner if you want to teletransmit your VAT return (there is no open/public API). Teledec is listed on the official `list of active EDI partners <https://www.impots.gouv.fr/portail/files/media/1_metier/3_partenaire/edi/liste_des_partenaires_edi_actifs.pdf>`_ under their legal name *LPI Conseil* with their official EDI partner reference 7500201.

This module supports EDI teletransmission of:
- 3310-CA3 monthly and quarterly,
- 3310-A (Appendix),
- 3514 (Credit VAT reimbursement).

The price of this EDI service for VAT returns is written on the `VAT page <https://www.teledec.fr/teledeclarer-et-payer-la-tva>`_ of the Teledec.fr website.
