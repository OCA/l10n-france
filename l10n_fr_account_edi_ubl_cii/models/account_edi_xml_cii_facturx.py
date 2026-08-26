# Copyright 2004-2015 Odoo S.A. (https://odoo.com)
# Copyright 2026 Le Filament (https://le-filament.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import models


class AccountEdiXmlCII(models.AbstractModel):
    _inherit = "account.edi.xml.cii"

    def _get_exchanged_document_vals(self, invoice):
        # Extend `account_edi_xml_cii` to add mandatory default notes [BR-FR-05]
        result = super()._get_exchanged_document_vals(invoice)

        result["included_note_list"].extend(
            [
                {
                    "subject_code": code,
                    "content": content,
                }
                for code, content in invoice._l10n_fr_get_default_notes().items()
            ]
        )

        return result
